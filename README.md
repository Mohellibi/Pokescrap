# Poké Scraper – EC2 → S3

> Scraper simple en Python pour récupérer les images des Pokémon depuis Bulbapedia, exécuté sur EC2, avec stockage automatique dans S3 via `boto3`.

## 0) Architecture (schéma)

```mermaid
flowchart LR
  subgraph AWS Account
    subgraph VPC
      EC2[EC2 - Amazon Linux 2<br/>Python + Script] -->|boto3 PutObject| S3[(S3 Bucket)]
    end
    IAM[IAM Role/Policy] -->|AssumeRole on EC2| EC2
    S3 -->|Public Read (Bucket Policy ou ACL)| Public[Internet Users]
  end
  Bulbapedia[(bulbapedia.bulbagarden.net)] -->|HTTPS GET (polite delay)| EC2
```

> Astuce draw.io: créer un diagramme "Flowchart" et coller le code Mermaid ci-dessus via **Arrange > Insert > Advanced > Mermaid**.

## 1) Mise en place EC2

1. Lancer une instance **Amazon Linux 2** (t2.micro suffit pour des tests).
2. Rôle IAM **attaché à l’instance** avec la *politique minimale* vers votre bucket S3 (exemple ci‑dessous).
3. Ouvrir le SG pour **egress** 443 (HTTPS). Pas d’ingress public requis (SSH via Session Manager recommandé).

### Politique S3 (exemple minimal)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:PutObjectAcl", "s3:ListBucket", "s3:HeadBucket"],
      "Resource": [
        "arn:aws:s3:::VOTRE_BUCKET",
        "arn:aws:s3:::VOTRE_BUCKET/*"
      ]
    }
  ]
}
```

> **Public access** : pour que les images soient publiques, choisissez **soit** une *bucket policy* "public read" (recommandé) **soit** ajoutez `--skip-public` et gérez la lecture publique via ACL bucket policy. Évitez d’ouvrir l’énorme `s3:*`.

## 2) Dépendances

```bash
sudo yum update -y  # ou apt
sudo yum install -y python3 git
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## 3) Configuration des identifiants (sécurisé)

- **Recommandé** : rôle IAM attaché à l’instance (aucune clé stockée).
- Alternative : `aws configure` avec un utilisateur IAM *aux permissions limitées*.
- Jamais de clés en dur dans le code. Un `.env.example` est fourni si vous voulez passer des options mais ce script se base sur `boto3` (chaines de credentials AWS standard).

## 4) Exécution

Test rapide (limiter à 10 Pokémon, délai 2s entre requêtes) :

```bash
python poke_scraper.py --bucket VOTRE_BUCKET --prefix images/national-dex --delay 2 --limit 10
```

Run complet :

```bash
python poke_scraper.py --bucket VOTRE_BUCKET --prefix images/national-dex --delay 2
```

## 5) Vérification et accès public

- **CLI** : `aws s3 ls s3://VOTRE_BUCKET/images/national-dex/ --recursive`
- **URL publique** : `https://VOTRE_BUCKET.s3.amazonaws.com/images/national-dex/0001-bulbasaur/0001Bulbasaur.png`

> Si l’URL retourne *AccessDenied*, vérifiez **Block Public Access**, la *bucket policy* ou l’option `--skip-public`.

## 6) Robustesse & bonnes pratiques

- Respect de `robots.txt` (le script vérifie et s’arrête si le chemin est interdit).
- **Delai** paramétrable `--delay` (par défaut 2s) pour limiter la charge.
- **Requêtes avec retries** + backoff (erreurs réseau/5xx).
- **Parsing résilient** : extraction des lignes par heuristique, puis récupération de **l’image de l’infobox** sur chaque page Pokémon (et conversion des URLs *thumb* vers l’original).
- **S3** : content-type correct, clés structurées `images/<categorie>/<dex>-<slug>/<filename>`.
- **Sécurité** : pas de secrets en dur; privilégier IAM Role; principe du moindre privilège.
- **Idempotence** : re‑lancer n’écrase pas un objet existant sans effet de bord (S3 `PutObject` remplace l’objet – acceptable ici; versioning recommandé si besoin).

## 7) Démonstration

- Placez ce repo sur EC2 (git clone ou scp), configurez le rôle IAM et exécutez la commande ci‑dessus.
- Capturez dans le README vos sorties `INFO Uploaded ...` et une capture d’écran S3 montrant les objets.

---

### Annexe : service systemd (optionnel)

Fichier `sample_systemd.service` fourni pour lancer en tâche de fond (adapter `User`, `WorkingDirectory`, `ExecStart`).

```ini
[Unit]
Description=Poke Scraper (one-off)
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/poke-scraper
Environment="PATH=/opt/poke-scraper/venv/bin"
ExecStart=/opt/poke-scraper/venv/bin/python /opt/poke-scraper/poke_scraper.py --bucket VOTRE_BUCKET --prefix images/national-dex --delay 2
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```