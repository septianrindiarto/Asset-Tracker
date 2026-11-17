# setup/

File di sini perlu disalin manual sekali ke lokasi akhirnya
(folder `.github` tidak bisa ditulis langsung oleh Claude).

```powershell
cd "D:\Project\Gold Tracker"
New-Item -ItemType Directory -Force .github\workflows | Out-Null   # buat folder .github\workflows bila belum ada
Copy-Item setup\github-workflows\*.yml .github\workflows\ -Force   # salin/menimpa 3 file workflow
```

Ulangi perintah `Copy-Item` setiap kali saya memberi tahu ada workflow baru/berubah.
