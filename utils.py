import os

def encontrar_pdfs(pasta):
    pdfs = []
    for arquivo in os.listdir(pasta):
        if arquivo.split(".")[0] == arquivo.split(".")[-1]:
            pdfs.append(encontrar_pdfs(pasta + "/" + arquivo)[-1])
        else:
            pdfs.append(pasta + "/" + arquivo)    
        
    return pdfs

def regra_divisao(pasta):
    for arquivo in os.listdir(pasta):
        print(arquivo)
        if arquivo.split('/')[-1] == "regras_divisao.txt":
            with open(pasta + "/" + arquivo, "r", encoding='utf-8') as f:
                return f.read().split(',')
            
    return ["divide by", 5]

def crop_page(pagina, rodape, cabecalho, margemEsq, margemDir):
    
    largura = pagina.width -margemDir
    altura = pagina.height - rodape

    page_crop = pagina.crop((margemEsq, cabecalho, largura, altura))

    return page_crop

def extrair_tabela_por_linhas_vermelhas(page_crop):
    """Detecta e recorta a área de uma tabela baseada em linhas vermelhas decorativas.

    Args:
        pagina: Um objeto `pdfplumber.page.Page`.
        rodape: Altura a ser cortada do rodapé (em pontos).
        mostrar: Se True, desenha círculos e imprime retângulos detectados.

    Returns:
        cropped_page: página recortada à área delimitada pelas linhas vermelhas (ou None se não encontrado).
    """

    def _eh_vermelho(color):
        if not color or len(color) < 3:
            return False
        r, g, b = color[:3]
        return 0.65 <= r <= 0.85 and 0.1 <= g <= 0.25 and 0.1 <= b <= 0.25

    elementos_vermelhos = [
        obj
        for obj in page_crop.rects + page_crop.curves
        if _eh_vermelho(obj.get("non_stroking_color"))
        or _eh_vermelho(obj.get("stroking_color"))
    ]

    red_rects = []
    for elem in sorted(elementos_vermelhos, key=lambda e: e.get("y1", 0)):
        if not red_rects:
            red_rects.append(elem.copy())
            continue

        last = red_rects[-1]
        if abs(elem.get("y1", 0) - last.get("y1", 0)) <= 5:
            last["x0"] = min(last.get("x0", 0), elem.get("x0", 0))
            last["y0"] = min(last.get("y0", 0), elem.get("y0", 0))
            last["x1"] = max(last.get("x1", 0), elem.get("x1", 0))
            last["y1"] = max(last.get("y1", 0), elem.get("y1", 0))
        else:
            red_rects.append(elem.copy())

    cropped = None
    if len(red_rects) >= 2:
        bbox = {
            "x0": min(r["x0"] for r in red_rects), "y0": min(r["top"] for r in red_rects),
            "x1": max(r["x1"] for r in red_rects), "y1": max(r["bottom"] for r in red_rects)
        }
        cropped = page_crop.crop((bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"]))

    return cropped