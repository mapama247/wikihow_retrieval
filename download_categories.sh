# Downloads the HTML code of all articles in the Spanish WikiHow, generating one file per category.
# Note: The 3 seconds delay between requests is just to prevent being banned, do not remove!

CATEGORIES=(
    "Adolescentes"
    "Arte-y-entretenimiento"
    "Automóviles-y-otros-vehículos"
    "Carreras-y-educación"
    "Comida-y-diversión"
    "Computadoras-y-electrónica"
    "Cuidado-y-estilo-personal"
    "Deportes"
    "Días-de-fiesta-y-tradiciones"
    "En-el-trabajo"
    "En-la-casa-y-el-jardín"
    "Filosofía-y-religión"
    "Finanzas-y-negocios"
    "Mascotas-y-animales"
    "Pasatiempos"
    "Relaciones"
    "Salud"
    "Viajes"
    "Vida-familiar"
)

for CATEGORY in ${CATEGORIES[@]}
do
    wget -r -l0 https://es.wikihow.com/Categoría:$CATEGORY --wait 3
done
