import pdfplumber
import math
from utils import encontrar_pdfs, regra_divisao, extrair_tabela_por_linhas_vermelhas, crop_page

print("Imports carregados")
pdf_folder = "arquivos/pastateste"

pdfs_encontrados = [f for f in encontrar_pdfs(pdf_folder) if f.lower().endswith(".pdf")]
print(f"Encontrados {len(pdfs_encontrados)} PDFs em {pdf_folder}")
for arquivo in pdfs_encontrados:
    print("-", arquivo)
# Escolha um PDF para analisar (altere o índice conforme necessário)
idx = 0
arquivo = pdfs_encontrados[idx]
print(f"Analisando: {arquivo}")

pagina_idx = 5

from IPython.display import display

def ajustar_linha(x_teorico, words, margem=15):
        """ Tenta mover o x_teorico para um espaço vazio próximo """
            
        # Procura palavras que estão "atropelando" a linha (dentro da margem)
        conflitos = [w for w in words if abs(w['x0'] - x_teorico) < margem or abs(w['x1'] - x_teorico) < margem]
        
        if not conflitos:
            return x_teorico # Linha já caiu no vazio
            
        # Se houver conflito, tentamos achar o maior "gap" de respiro perto da linha
        # Encontramos o x1 da palavra à esquerda e o x0 da palavra à direita da linha
        esquerdas = [w['x1'] for w in conflitos if w['x1'] < x_teorico]
        direitas = [w['x0'] for w in conflitos if w['x0'] > x_teorico]
        
        novo_x = x_teorico
        if esquerdas and direitas:
            # Coloca a linha exatamente no meio do espaço entre as palavras
            novo_x = (max(esquerdas) + min(direitas)) / 2
        elif esquerdas:
            novo_x = max(esquerdas) + 2 # Cola logo após a palavra da esquerda
        elif direitas:
            novo_x = min(direitas) - 2 # Cola logo antes da palavra da direita
            
        return novo_x

def filtrar_e_ajustar_h_lines(h_coords, words, margem_busca=5):
    """ 
    Remove linhas horizontais que estão no 'vazio' 
    e ajusta as que sobraram para os limites do texto.
    """
    h_validadas = []
    
    # Sempre mantemos a primeira e a última (bordas da tabela)
    if not h_coords: return []
    h_validadas.append(h_coords[0])
    
    for y_teorico in h_coords[1:-1]:
        # Busca palavras que terminam logo acima ou começam logo abaixo desta linha
        palavras_perto = [
            w for w in words 
            if abs(w['bottom'] - y_teorico) < margem_busca 
            or abs(w['top'] - y_teorico) < margem_busca
        ]
        
        # Se houver texto perto, essa linha é real!
        if palavras_perto:
            # Opcional: Ajustar o Y para o ponto médio exato do "respiro" entre linhas
            # Isso deixa a extração muito mais limpa
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
    page = pdf.pages[pagina_idx]
    # paginas = page.extract_text_lines()
    # for pag in paginas:
    #     print(pag['text'])
    cropped = crop_page(page, 120, 100, 30, 30)
    # display(cropped.to_image(100))

    v_coords = sorted(list(set([
        cropped.bbox[0],              
        # cropped.rects[0]['x1'],       
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

    table = cropped.extract_tables(table_settings=table_settings)
    for i, lin in enumerate(table[0]):
        if (lin[0] == ''): table[0].pop(i)
    for i, lin in enumerate(table[0]):
        if (lin[0] == 'Hora'): table[0].pop(i)
    for i, lin in enumerate(table[0]):
        print(lin)
    # table.remove(['']) ENTRAR DENTRO DE ITENS DA TABELA PARA REMOVER ESPAÇOS VAZIOS
    # table[0][0].remove('')
    # for dia in table[0]:
    #     for i, item in enumerate(dia):
    #         if item != '': dia.pop(i)
    #         print(dia)