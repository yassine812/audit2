import fitz

doc = fitz.open(r"C:\Users\Yassine\.gemini\antigravity-ide\brain\f47ebb93-79f7-4d31-aa2e-0fd20197b3c7\.user_uploaded\media_1788168897234.pdf")
print("Total pages in official Doc.83:", len(doc))

page1 = doc[0]
pix = page1.get_pixmap()
pix.save("doc83_page1.png")
print("Saved doc83_page1.png")
