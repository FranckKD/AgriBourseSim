# export_tools.py
import pandas as pd
import io
from fpdf import FPDF
import matplotlib.pyplot as plt
from PIL import Image


def export_excel(resultats: dict, nom_fichier: str = "export.xlsx") -> bytes:
    """
    Génère un fichier Excel à partir des résultats de simulation.
    """
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for nom_feuille, df in resultats.items():
            if isinstance(df, pd.DataFrame):
                df.to_excel(writer, sheet_name=nom_feuille)
    buffer.seek(0)
    return buffer.getvalue()


class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Rapport de Simulation", ln=True, align="C")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def chapter_title(self, title):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, title, ln=True, align="L")
        self.ln(5)

    def chapter_body(self, content):
        self.set_font("Arial", "", 10)
        self.multi_cell(0, 10, content)
        self.ln()

    def add_table(self, dataframe: pd.DataFrame):
        self.set_font("Arial", "", 9)
        col_width = self.w / (len(dataframe.columns) + 1)
        for col in dataframe.columns:
            self.cell(col_width, 10, col, 1)
        self.ln()
        for _, row in dataframe.iterrows():
            for item in row:
                self.cell(col_width, 10, str(item), 1)
            self.ln()

    def add_image(self, image_path):
        self.image(image_path, w=self.w - 40)
        self.ln()


def export_pdf(resultats: dict, graphiques: dict = None, nom_fichier: str = "export.pdf") -> bytes:
    pdf = PDF()
    pdf.add_page()

    for titre, contenu in resultats.items():
        pdf.chapter_title(titre)
        if isinstance(contenu, pd.DataFrame):
            pdf.add_table(contenu)
        elif isinstance(contenu, str):
            pdf.chapter_body(contenu)

    if graphiques:
        for nom_fig, fig in graphiques.items():
            image_path = f"/tmp/{nom_fig}.png"
            fig.savefig(image_path)
            pdf.add_page()
            pdf.chapter_title(f"Graphique : {nom_fig}")
            pdf.add_image(image_path)

    return pdf.output(dest='S').encode('latin1')