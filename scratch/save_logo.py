import os, shutil

src = r"C:\Users\Yassine\.gemini\antigravity-ide\brain\f47ebb93-79f7-4d31-aa2e-0fd20197b3c7\.user_uploaded\media_1788186244857.png"

dest_dirs = [
    r"c:\Users\Yassine\audit2-main\reclamation_client\static\reclamation_client",
    r"c:\Users\Yassine\audit2-main\assets",
]

for d in dest_dirs:
    os.makedirs(d, exist_ok=True)
    dst_file = os.path.join(d, "ab_serve_logo.png")
    shutil.copy(src, dst_file)
    print(f"Copied logo to {dst_file}")

print("Logo saved successfully.")
