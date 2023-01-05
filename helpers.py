from fpdf import FPDF
import os

"""

r = "reagent"
n = "newlot"
c = "currentlot"
rr = "received"
p = "prepared"
e = "expired"
i = "initials"
d = "date"
image = "static/files/test.png"

listo = [r, n, c,  rr, p, e, i, d]
"""
#[{'reagent': 'knj', 'newlot': '546', 'currentlot': '456', 'received': '2022-12-20', 'prepared': '2022-12-20', 'expired': '2022-12-20', 'initials': 'mn', 'QC_date': '2022-12-20'}]



class PDF(FPDF):
    def header(self):
        # Setting font: helvetica bold 15
        self.set_font("helvetica", "B", 15)
        # Moving cursor to the right:
        self.cell(80)
        # Printing title:
        self.cell(30, 10, "Reagent Quality Control Worksheet", align="C")
        # Performing a line break:
        self.ln(20)

# problem/bug: need to ensure constant dimensions of the images uploaded
def makePDF(var_list, pic3, pic1, pic2):
    titulos = ["Reagent name", "Lot number", "Current/Old lot", "Date received", "Date prepared", "Date of expiry", "MLS initials", "Date QC performed", "Comment"]
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Times", size=12)
    for i in range(len(var_list)):
            pdf.cell(0, 10, f"{titulos[i]}: {var_list[i]}", new_x="LMARGIN", new_y="NEXT")
    pdf.image(pic3, w=100)
    pdf.image(pic1, w=100)
    pdf.image(pic2, w=100)
    pdf.output(f'static/pdfs/{var_list[0]}.pdf')


def makeFinalPDF(var_list, pic3, pic1, pic2):
    titulos = ["Reagent name", "Lot number", "Current/Old lot", "Date received", "Date prepared", "Date of expiry", "MLS initials", "Date QC performed", "Comment", "Date of Review", "Reviewer initials"]
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Times", size=12)
    for i in range(len(var_list)):
            pdf.cell(0, 10, f"{titulos[i]}: {var_list[i]}", new_x="LMARGIN", new_y="NEXT")
    pdf.image(pic3, w=100)
    pdf.image(pic1, w=100)
    pdf.image(pic2, w=100)
    pdf.output(f'static/final_pdfs/{var_list[0]}.pdf')


def convert_data(data, file_name):
    # Convert binary format to images or files data
    with open(file_name, 'wb') as file:
        file.write(data)


def main():
    makePDF(listo, image)


if __name__ == "__main__":
   main()