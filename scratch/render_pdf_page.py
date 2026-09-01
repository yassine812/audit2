import fitz
doc = fitz.open("REC2608010_Oui_Non_Cols.pdf")

page1 = doc[0]
pix1 = page1.get_pixmap(dpi=150)
pix1.save("c:/Users/Yassine/audit2-main/scratch/preview_p1.png")

page2 = doc[1]
pix2 = page2.get_pixmap(dpi=150)
pix2.save("c:/Users/Yassine/audit2-main/scratch/preview_p2.png")

print("Saved preview_p1.png and preview_p2.png")
