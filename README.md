# PHP + Jenkins + Nessus - Repo de ejemplo

Este repo es una app php mínima para demostrar integración con Jenkins, Nessus (escaneo), conversión a PDF con Pandoc y envío de reporte.

## Pasos rápidos
1. Subir repo a GitHub.
2. Crear carpeta de credenciales en Jenkins:
   - NESSUS_ACCESS_KEY (Secret text)
   - NESSUS_SECRET_KEY (Secret text)
   - NESSUS_URL (URL base)
3. Crear job de tipo *Pipeline* en Jenkins apuntando a este repo.
4. Asegurarse que el agente Jenkins tiene:
   - node/npm instalado
   - pandoc (y wkhtmltopdf opcional)
   - acceso a la API de Nessus (si usas Nessus)
5. Ejecutar pipeline.

## Notas
- `scripts/scan_nessus.sh` es un ejemplo: debes adaptarlo a la API de tu servidor Nessus o usar `nessuscli`.
- `Jenkinsfile` utiliza `emailext` (plugin Email Extension). Ajusta según tu configuración de correo.
