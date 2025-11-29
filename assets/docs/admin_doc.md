# INSOMNIA SEO-INJECTOR — Admin Documentation
## Ringkasan
Dokumen ini menjelaskan alur sistem lisensi offline (RSA-signed JWT), struktur project, cara generate license (admin), penyimpanan key, dan cara me-manage dokumentasi langsung dari dashboard admin.




---




## 1. Arsitektur Lisensi (Offline RS256)
- Admin memegang **private_key.pem** (private RSA key) — **JANGAN** publish.
- Client (app user) menerima license token (JWT RS256 string).
- Client bundling berisi **public_key.pem** untuk verifikasi offline.
- JWT payload minimal:
- `sub`: user id
- `type`: "admin" | "user"
- `features`: ["traffic", "backlink", ...]
- `iat`, `exp`, `jti` (opsional)




**Keunggulan:** verifikasi offline tanpa server.
**Kelemahan:** tidak bisa revoke kecuali ditambahkan server check periodik.




---




## 2. Langkah Cepat — Generate Keypair (Admin)
1. Jalankan generator (menu **Generate Keypair** di Dashboard Admin).
2. Script akan membuat:
- `private_key.pem` (simpan offline & aman)
- `public_key.pem` (bundle ke client)
3. Simpan backup private key di vault yang aman (USB/KeyVault).
4. Berikan `public_key.pem` ke team build untuk di-bundle ke installer.




> **PENTING:** jangan commit `private_key.pem` ke repo.




---




## 3. Langkah Cepat — Generate License Token (Admin)
1. Buka menu **Generate License**.
2. Isi: `user_id`, `license_type`, `days_valid`, `features`.
3. Klik **Generate** → muncul satu string token (JWT).
4. Klik **Copy** untuk menyalin token.




**Distribusi**: kirim token ke user (email/WhatsApp/dll) atau tampilkan QR untuk discan.




---




## 4. Flow Aktivasi (Client)
1. User buka app → tampilan Auth Page → paste token.
2. App verify token dengan `public_key.pem`.
3. Jika valid, simpan `config.json`:
```json
{
"activated": true,
"license": {
"token": "<JWT>",
"user": "user_123",
"exp": "2026-11-08T00:00:00Z",
"features": ["traffic","backlink"]
}
}