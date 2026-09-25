[Read in English](README.md)

# Job Market Pulse

Pipeline ETL qui suit chaque semaine la demande de compétences sur le marché de l'emploi data (postes Data Analyst et Data Engineer), depuis l'extraction de deux APIs jusqu'à un dashboard prêt pour l'analyse.

Projet construit pour démontrer une chaîne complète d'ingénierie de données ; extraction Python, orchestration Airflow, stockage cloud AWS, modélisation SQL dimensionnelle, tests, visualisation. Le tout gratuit de bout en bout, dans les limites du free tier AWS.

![Dashboard Job Market Pulse](docs/images/dashboard.png)

## Ce que ça fait

Chaque semaine, le pipeline interroge deux sources d'offres d'emploi (Remotive pour le full remote, Adzuna pour une couverture multi pays), normalise les résultats vers un schéma commun, les dépose sur S3, puis les charge dans un entrepôt de données PostgreSQL structuré en modèle en flocon. Des vues agrégées, le datamart, alimentent ensuite un dashboard qui répond à des questions concrètes : quelles compétences reviennent le plus dans les offres, quelle est la répartition par niveau de séniorité, quels pays concentrent la demande.

## Stack technique

Python pour l'extraction et la transformation ; Apache Airflow pour l'orchestration, avec vérification des APIs en amont via des sensors, retries automatiques et alertes email en cas d'échec ; Amazon S3 pour la zone brute, partitionnée par date ; Amazon RDS PostgreSQL comme entrepôt ; Metabase pour la visualisation ; pytest pour les tests unitaires de la logique métier. Tout orchestré en local via Docker.

## Architecture

```
Remotive API ─┐
              ├─► Extraction Python ─► S3 (raw, partitionné par date)
Adzuna API ───┘                              │
                                             ▼
                                    Staging PostgreSQL
                                             │
                              (détection compétences, séniorité,
                               géographie, filtrage de pertinence)
                                             │
                                             ▼
                              Entrepôt en flocon (dwh)
                         fact_job_posting, dim_company, dim_skill,
                            dim_city, dim_country, dim_date
                                             │
                                             ▼
                                Datamart (vues agrégées)
                                             │
                                             ▼
                                        Dashboard
```

L'ensemble est orchestré par un DAG Airflow unique, déclenché chaque lundi, avec un enchaînement clair : vérification des APIs, extraction et upload S3, chargement en staging, transformation vers l'entrepôt.

## Pourquoi ces choix

**Deux sources plutôt qu'une.** Remotive est spécialisée dans le remote mais son volume reste modeste ; Adzuna couvre plusieurs pays européens avec un volume plus large. Combiner les deux, avec une traçabilité de la source sur chaque offre, donne une vision plus complète sans dépendre d'un seul fournisseur de données.

**Un modèle en flocon plutôt qu'une table plate.** La géographie est normalisée en cascade, ville puis pays, plutôt que répétée sur chaque ligne. Ça évite les incohérences de nommage et reste cohérent avec ce qu'on attend d'un vrai entrepôt de données en entreprise.

**Capturer large, filtrer précisément plus tard.** L'extraction ne rejette que les intitulés clairement hors sujet ; le vrai filtre de pertinence métier, les compétences détectées, le niveau de séniorité, est appliqué au moment du chargement dans l'entrepôt. Cette séparation permet d'ajuster la logique de filtrage sans jamais avoir à relancer une extraction.

**Des vues plutôt que des tables matérialisées pour le datamart.** Le volume de données de ce projet reste modeste, une vue recalculée à la demande garantit qu'elle reflète toujours l'état actuel de l'entrepôt sans aucune tâche de rafraîchissement supplémentaire. Sur un volume nettement plus important, la bonne pratique serait de migrer vers des vues matérialisées, rafraîchies explicitement depuis le DAG.

## Ce que montre le dashboard

Le dashboard regroupe quatre indicateurs de synthèse (nombre total d'offres, nombre d'entreprises distinctes, part de remote, date de dernière mise à jour), puis trois visuels détaillés : les compétences les plus demandées, la répartition par niveau de séniorité, et la répartition géographique.

Un point à préciser honnêtement sur la lecture du graphique de séniorité : la majorité des offres apparaissent en "unknown". Ce n'est pas un problème de données, c'est une limite assumée de la méthode ; le niveau recherché est déduit uniquement du titre de l'offre, et beaucoup d'offres ne précisent leur niveau que dans le corps de la description, pas dans le titre. Une évolution possible serait d'étendre cette détection à la description complète.

## Visualisation, Metabase et Power BI

Le dashboard principal a été construit avec Metabase, un outil open source qui tourne nativement sur macOS via Docker, sans les contraintes de Power BI Desktop qui reste réservé à Windows.

La connexion à l'entrepôt a aussi été testée depuis Power BI, en se branchant directement sur la même base RDS ; un simple refresh suffit pour récupérer les données à jour produites par le pipeline. Ce test confirme que l'entrepôt est agnostique de l'outil de visualisation, la même base peut alimenter plusieurs consommateurs sans aucune modification. Dans ce projet précis, toute la transformation est déjà assurée en amont par le pipeline Python et SQL, donc les deux outils se valent pour un usage de pure restitution. Power BI prendrait tout son sens si une transformation supplémentaire via Power Query était nécessaire directement dans l'outil, ce qui n'était pas le cas ici.

## Structure du projet

```
dags/                DAG Airflow
src/
  extract/            clients API, normalisation, filtrage
  transform/           chargement staging, transformation vers l'entrepôt
  load/                 upload S3
sql/
  ddl/                 schémas staging, entrepôt, datamart
  transform/            équivalent SQL pur de la transformation Python
tests/                 tests unitaires
docker-compose.yaml    orchestration Airflow en local
```

## Faire tourner le projet

Prérequis : un compte AWS (free tier), Docker Desktop, Python 3.11 ou plus récent.

```bash
git clone https://github.com/TON_USERNAME/Job_Market_Pulse.git
cd Job_Market_Pulse
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # à compléter avec ses propres identifiants
```

Créer le bucket S3 et l'instance RDS PostgreSQL, puis exécuter les scripts SQL dans `sql/ddl/` dans l'ordre. Lancer ensuite Airflow :

```bash
docker compose up airflow-init
docker compose up -d
```

Le DAG `job_market_pulse_etl` est visible sur `localhost:8080`, à déclencher manuellement ou à laisser tourner selon son planning hebdomadaire.

## Limite connue et piste d'évolution

Le pipeline tourne aujourd'hui en local, via Docker sur un Mac. Le déclenchement hebdomadaire automatique ne peut donc avoir lieu que si la machine est allumée et connectée à ce moment précis, une vraie limite pour une exécution réellement autonome. La suite logique consiste à déployer exactement le même `docker-compose.yaml` sur une instance EC2 qui reste active en permanence, sans changer une seule ligne de la logique métier du pipeline.

