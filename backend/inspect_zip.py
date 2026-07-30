import zipfile
import os

zip_path = r"C:\dev\simulation-sandbox\simulation-sandbox\files.zip"
if os.path.exists(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as z:
        print(f"Archive: {zip_path}")
        print(f"Entries: {len(z.namelist())}")
        for name in z.namelist()[:30]:
            info = z.getinfo(name)
            print(f"  {name} ({info.file_size} bytes)")
else:
    print("files.zip not found")
