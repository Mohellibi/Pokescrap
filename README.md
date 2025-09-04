# poke_scraper

Ce script télécharge les images des Pokémon depuis Bulbapedia et le clone de ce repo github dans EC2 et les envoie dans un bucket S3 AWS.

## Prérequis

- Python 3.7+
- une instance EC2 avec le role adaptée
- Un bucket S3 nommé `bucket-pokemon2`
- Les identifiants AWS configurés (`aws configure`)

## Installation

Installez les dépendances nécessaires :

```bash
pip install -r requirements.txt
```

## Utilisation

```bash
git clone https://github.com/Mohellibi/Pokescrap
cd /Pokescrap
python poke_scraper.py --bucket bucket-pokemon2 --prefix images --limit 10
```

- `--bucket` : nom du bucket S3 (doit être `bucket-pokemon2`)
- `--prefix` : préfixe S3 (doit commencer par `images`)
- `--limit` : nombre de Pokémon à traiter (optionnel)

## Notes

- Le script respecte la politique AWS fournie.
- Les images sont stockées sous le préfixe `images/` dans le bucket.
