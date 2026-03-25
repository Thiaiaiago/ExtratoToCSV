import pdfplumber
import math
import pandas
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from utils import encontrar_pdfs, crop_page

print("Imports carregados")

pdf_folder = "arquivos"

pdfs_encontrados = [f for f in encontrar_pdfs(pdf_folder) if f.lower().endswith(".pdf")]
print(f"Encontrados {len(pdfs_encontrados)} PDFs em {pdf_folder}")
for arquivo in pdfs_encontrados:
    print("-", arquivo)

idx = 0
arquivo = pdfs_encontrados[idx]
print(f"Analisando: {arquivo}")

pagina_idx = 5

def ajustar_linha(x_teorico, words, margem=15):
        """ Tenta mover o x_teorico para um espaço vazio próximo """
            
        conflitos = [w for w in words if abs(w['x0'] - x_teorico) < margem or abs(w['x1'] - x_teorico) < margem]
        
        if not conflitos:
            return x_teorico 
        
        esquerdas = [w['x1'] for w in conflitos if w['x1'] < x_teorico]
        direitas = [w['x0'] for w in conflitos if w['x0'] > x_teorico]
        
        novo_x = x_teorico
        if esquerdas and direitas:
            novo_x = (max(esquerdas) + min(direitas)) / 2
        elif esquerdas:
            novo_x = max(esquerdas) + 2 
        elif direitas:
            novo_x = min(direitas) - 2
            
        return novo_x

def filtrar_e_ajustar_h_lines(h_coords, words, margem_busca=5):
    """ 
    Remove linhas horizontais que estão no 'vazio' 
    e ajusta as que sobraram para os limites do texto.
    """
    h_validadas = []
    
    if not h_coords: return []
    h_validadas.append(h_coords[0])
    
    for y_teorico in h_coords[1:-1]:
        palavras_perto = [
            w for w in words 
            if abs(w['bottom'] - y_teorico) < margem_busca 
            or abs(w['top'] - y_teorico) < margem_busca
        ]
        
        if palavras_perto:
            tops_abaixo = [w['top'] for w in palavras_perto if w['top'] > y_teorico]
            bottoms_acima = [w['bottom'] for w in palavras_perto if w['bottom'] < y_teorico]
            
            if tops_abaixo and bottoms_acima:
                y_ajustado = (max(bottoms_acima) + min(tops_abaixo)) / 2
                h_validadas.append(y_ajustado)
            else:
                h_validadas.append(y_teorico)
                
    h_validadas.append(h_coords[-1])
    return sorted(list(set(h_validadas)))

with pdfplumber.open(arquivo) as pdf:
    tables = []
    for page in pdf.pages:
    # page = pdf.pages[pagina_idx]
        cropped = crop_page(page, 120, 100, 30, 30)
        
        if "Extrato" in cropped.extract_text_lines()[0]['text']:
            cropped = crop_page(page, 120, 200, 30, 30)

        v_coords = sorted(list(set([
            cropped.bbox[0],              
            cropped.bbox[2]               
        ])))

        table_settings_lines = {
            "horizontal_strategy": "text", 
            "snap_y_tolerance": 4,
            "join_tolerance": 5,
            "min_words_vertical": 1
        }

        finder = cropped.debug_tablefinder(table_settings=table_settings_lines)
        hlines_tops = [int(line['top']) for line in finder.edges]

        for i, line in enumerate(hlines_tops):
            if i > 0 and i < (len(hlines_tops)-1) and math.isclose((hlines_tops[i+1] - line), (line - hlines_tops[i-1]), rel_tol=0.2):
                hlines_tops.pop(i)

        words = cropped.extract_words()
        h_coords_limpas = filtrar_e_ajustar_h_lines(hlines_tops, words)

        table_settings_cols = {
            "vertical_strategy": "text", 
            "snap_y_tolerance": 4,
            "join_tolerance": 5,
            "min_words_vertical": 1
        }

        finder = cropped.debug_tablefinder(table_settings=table_settings_cols)
        vlines_tops = [int(line['x0']) for line in finder.edges]
        
        for i, line in enumerate(vlines_tops):
            if i > 0 and i < (len(vlines_tops)-1):
                if ((vlines_tops[i+1] - line) < 20):
                    vlines_tops.pop(i)

        words = cropped.extract_text_lines()
        
        lines = [i for i in range(0, page.width, round(page.width/5))]
        linhas_ajustadas = [ajustar_linha(l, words, 100) for l in lines]
        linhas_ajustadas.append(cropped.extract_text_lines()[-2]['x1'])
        
        table_settings = {
            "vertical_strategy": "explicit",
            "explicit_vertical_lines": linhas_ajustadas,
            "horizontal_strategy": "explicit", 
            "explicit_horizontal_lines": h_coords_limpas,
            "snap_y_tolerance": 4,
            "join_tolerance": 5,
        }

        pag_tables = cropped.extract_tables(table_settings=table_settings)
        
        if pag_tables:
            linhas_da_pagina = [lin for lin in pag_tables[0] if lin[0] != '' and lin[0] != 'Hora']
            tables.extend(linhas_da_pagina)

    tabelaFinal = {}
    meses_map = {'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04', 'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08', 'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'}
                
    for lin in tables:
        if '2026' in lin [0]:
            data = lin[0]
            splitedData = data.split(' ')
            formatData = splitedData[-1] + '-' + meses_map[splitedData[2]] + '-' + splitedData[0]
            tabelaFinal[formatData] = []
        else:
            tabelaFinal[formatData].append(lin)

    dados_para_pandas = []
    for data, transacoes in tabelaFinal.items():
        for t in transacoes:
            linha = {
                "Data da compra": data,
                "Data do pagamento": data if "Pix" in t[1] else "",
                "Valor": t[-1].replace('R$ ', ''),
                "Grupo": "ENTRADA" if "recebido" in t[1] else "SAIDA" if "enviado" in t[1] else "",
                "Forma de pagamento": "Pix" if "Pix" in t[1] else "",
                "Estabelecimento": t[2],
                "Pago": "True" if "Pix" in t[1] else "False",
                "Banco": "Picpay",
                "Mês do pagamento": "",
                "Categoria": "",
                "Descrição": "",
                "Observação": "",
                "Parcelas": ""
            }
            dados_para_pandas.append(linha)
    df = pandas.DataFrame(dados_para_pandas)
    df = df.sort_values(by="Data da compra").reset_index(drop=True)

    df_antigo = pandas.read_excel("arquivos/Finanças Pessoais.xlsx")
    
    dfFinal = pandas.concat([df_antigo, df], ignore_index=True)
    df_estilizado = dfFinal.style.apply(lambda x: ['background-color: #a1ffbb' if x.name >= len(df_antigo) else '' for _ in x], axis=1)

    df_antigo.to_excel("teste.xlsx", index=False)
    df_estilizado.to_excel("extrato_final.xlsx", engine='openpyxl', index=False)

    import gspread
    from google.oauth2.service_account import Credentials

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("arquivos/credencial.json", scopes=scope)
    client = gspread.authorize(creds)

    planilha = client.open("Finanças Pessoais").sheet1
    colunas_no_sheets = planilha.row_values(1) 

    df_novo_ordenado = df[colunas_no_sheets]

    dados_para_adicionar = df_novo_ordenado.values.tolist()

if dados_para_adicionar:
    planilha.append_rows(dados_para_adicionar, value_input_option='USER_ENTERED')
    print("✅ Colunas alinhadas e dados enviados com sucesso!")
