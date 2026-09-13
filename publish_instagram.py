#!/usr/bin/env python3
"""
Publish Instagram — publie un post (image unique ou carrousel) sur Instagram via
l'API Graph, à partir d'un dossier de post de la convention trek-my-mind
(<série>/<Jxx-titre>/publication.json + photos/).

Prérequis : pip install requests
Variables d'environnement requises (jamais en argument CLI — historique shell) :
    IG_USER_ID        ID du compte Instagram (flux Instagram API with Instagram
                       Login — récupéré via /me sur graph.instagram.com, pas
                       l'ID d'app ni un ID lié à une Page Facebook)
    META_ACCESS_TOKEN token Instagram natif (préfixe IGAA...) — longue durée si
                       possible, court terme accepté pour un test ponctuel

L'API Graph ne permet aucun upload de fichier local : elle exige une URL HTTPS
publique par image (elle la télécharge elle-même). Convention retenue : dépôt GitHub
public — l'URL raw.githubusercontent.com est déduite automatiquement du remote git et
de la branche courante du dossier série (donc du dépôt trek-my-mind).

Usage :
    python publish_instagram.py --post ~/Dev/trek-my-mind/3-cols-khumbu/J08-col-kongma
    python publish_instagram.py --post ... --publier   # publie réellement (sinon dry-run)

Dry-run par défaut (sans --publier) : valide les URLs, crée et vérifie les conteneurs
médias, affiche ce qui serait publié — s'arrête avant le seul appel irréversible
(media_publish). Un post doit être au statut 'pret' dans publication.json (jamais
'brouillon', jamais déjà 'publie') pour être traité, même en dry-run.

Identité du post : au moins une slide doit porter le suffixe -scene ou -titre (rendu
/masque-photos --serie), sauf montage hors-série (ex. 00-manifeste, 01-ouverture-dolpo)
qui porte un champ "identite": "manuelle" dans publication.json — posé à la main une
fois l'identité éditoriale du post confirmée par ailleurs (titre + légende).
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

# Flux retenu (11/09/2026) : Instagram API with Instagram Login — IG_USER_ID et
# META_ACCESS_TOKEN natifs Instagram (token IGAA..., pas EAA...), domaine
# graph.instagram.com (pas graph.facebook.com, incompatible avec ce type de token).
# Versions Graph API publiées ~2x/an — à vérifier/ajuster lors de la création de l'app
# développeur Meta (cf. developers.facebook.com), ce défaut peut être obsolète.
GRAPH_API_VERSION = os.environ.get("META_GRAPH_API_VERSION", "v23.0")
GRAPH_API_BASE = f"https://graph.instagram.com/{GRAPH_API_VERSION}"

POLL_INTERVAL_S = 3
POLL_TIMEOUT_S = 120


def env_or_exit(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"✗ Variable d'environnement {name} manquante — jamais en argument CLI. "
              f"Exporter {name} avant de relancer.", file=sys.stderr)
        sys.exit(1)
    return value


def github_raw_base_url(repo_dir: Path) -> str:
    """Déduit l'URL de base raw.githubusercontent.com depuis le remote 'origin' et la
    branche courante du dépôt git contenant `repo_dir`."""
    try:
        remote = subprocess.run(["git", "-C", str(repo_dir), "remote", "get-url", "origin"],
                                 capture_output=True, text=True, check=True).stdout.strip()
        branch = subprocess.run(["git", "-C", str(repo_dir), "rev-parse", "--abbrev-ref", "HEAD"],
                                 capture_output=True, text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"✗ Impossible de lire le remote/la branche git de {repo_dir} : {e}", file=sys.stderr)
        sys.exit(1)

    remote = remote.removesuffix(".git")
    if remote.startswith("git@github.com:"):
        owner_repo = remote.removeprefix("git@github.com:")
    elif "github.com/" in remote:
        owner_repo = remote.split("github.com/", 1)[1]
    else:
        print(f"✗ Remote non reconnu (attendu GitHub) : {remote}", file=sys.stderr)
        sys.exit(1)

    return f"https://raw.githubusercontent.com/{owner_repo}/{branch}"


def find_repo_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / ".git").is_dir():
            return parent
    print(f"✗ Dépôt git introuvable en remontant depuis {start}", file=sys.stderr)
    sys.exit(1)


def image_url_for(photo_path: Path, repo_root: Path, raw_base: str) -> str:
    rel = photo_path.relative_to(repo_root)
    return f"{raw_base}/{rel.as_posix()}"


def check_url_reachable(url: str):
    try:
        r = requests.head(url, timeout=10, allow_redirects=True)
    except requests.RequestException as e:
        print(f"✗ URL image injoignable : {url} ({e})", file=sys.stderr)
        sys.exit(1)
    if r.status_code != 200:
        print(f"✗ URL image injoignable (HTTP {r.status_code}) : {url} — vérifier que le "
              f"fichier est bien poussé sur GitHub", file=sys.stderr)
        sys.exit(1)


def graph_post(path: str, params: dict, access_token: str) -> dict:
    data = graph_request(requests.post, path, params, access_token)
    return data


def graph_get(path: str, params: dict, access_token: str) -> dict:
    return graph_request(requests.get, path, params, access_token)


def graph_request(method, path: str, params: dict, access_token: str) -> dict:
    payload = {**params, "access_token": access_token}
    kwargs = {"params": payload} if method is requests.get else {"data": payload}
    r = method(f"{GRAPH_API_BASE}/{path}", timeout=30, **kwargs)
    data = r.json()
    if "error" in data:
        err = data["error"]
        print(f"✗ Erreur API Graph ({path}) : {err.get('message')} (code {err.get('code')})",
              file=sys.stderr)
        sys.exit(1)
    return data


def wait_container_ready(container_id: str, access_token: str):
    """Attend qu'un conteneur média passe à FINISHED (poll de status_code) — échoue
    explicitement sur ERROR ou si POLL_TIMEOUT_S est dépassé."""
    deadline = time.monotonic() + POLL_TIMEOUT_S
    while time.monotonic() < deadline:
        data = graph_get(container_id, {"fields": "status_code"}, access_token)
        status = data.get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            print(f"✗ Conteneur {container_id} en erreur : {data}", file=sys.stderr)
            sys.exit(1)
        time.sleep(POLL_INTERVAL_S)
    print(f"✗ Délai dépassé en attendant le conteneur {container_id} (statut non FINISHED)",
          file=sys.stderr)
    sys.exit(1)


def create_image_container(ig_user_id: str, access_token: str, image_url: str, *,
                            caption: str | None = None, is_carousel_item: bool = False) -> str:
    params = {"image_url": image_url}
    if caption is not None:
        params["caption"] = caption
    if is_carousel_item:
        params["is_carousel_item"] = "true"
    return graph_post(f"{ig_user_id}/media", params, access_token)["id"]


def create_carousel_container(ig_user_id: str, access_token: str, children_ids: list[str],
                               caption: str) -> str:
    params = {"media_type": "CAROUSEL", "children": ",".join(children_ids), "caption": caption}
    return graph_post(f"{ig_user_id}/media", params, access_token)["id"]


def publish_container(ig_user_id: str, access_token: str, container_id: str) -> str:
    return graph_post(f"{ig_user_id}/media_publish", {"creation_id": container_id}, access_token)["id"]


def load_publication(post_dir: Path) -> dict:
    pub_path = post_dir / "publication.json"
    if not pub_path.exists():
        print(f"✗ publication.json introuvable : {pub_path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(pub_path.read_text())


def main():
    parser = argparse.ArgumentParser(
        description="Publie un post Instagram (image unique ou carrousel) via l'API Graph, "
                     "à partir d'un dossier de post de la convention trek-my-mind.")
    parser.add_argument("--post", type=Path, required=True,
                         help="Dossier du post (contient publication.json et photos/), ex. "
                              "~/Dev/trek-my-mind/3-cols-khumbu/J08-col-kongma")
    parser.add_argument("--publier", action="store_true",
                         help="Publie réellement sur Instagram (media_publish). Sans ce flag : "
                              "dry-run — s'arrête après validation et création des conteneurs.")
    args = parser.parse_args()

    post_dir = args.post.expanduser().resolve()
    if not post_dir.is_dir():
        print(f"✗ Dossier post introuvable : {post_dir}", file=sys.stderr)
        sys.exit(1)

    entry = load_publication(post_dir)

    if entry.get("statut") != "pret":
        print(f"✗ Statut actuel : {entry.get('statut')!r} — seul un post au statut 'pret' peut "
              f"être traité (jamais 'brouillon', jamais déjà 'publie'), y compris en dry-run.",
              file=sys.stderr)
        sys.exit(1)

    slides = entry.get("slides") or []
    if not slides:
        print(f"✗ Champ 'slides' vide dans {post_dir / 'publication.json'} — lister les photos "
              f"finales (noms de fichiers dans photos/, dans l'ordre du carrousel) avant de "
              f"publier.", file=sys.stderr)
        sys.exit(1)

    if len(slides) > 10:
        print(f"✗ {len(slides)} slides dans {post_dir / 'publication.json'} — l'API Graph "
              f"limite un carrousel Instagram à 10 images maximum (erreur 'Unsupported post "
              f"type' sinon). Réduire 'slides' à 10 ou moins, ou scinder le post en plusieurs.",
              file=sys.stderr)
        sys.exit(1)

    legende = entry.get("legende")
    if not legende:
        print("✗ Champ 'legende' vide — rien à publier sans légende.", file=sys.stderr)
        sys.exit(1)

    hashtags = entry.get("hashtags") or []
    if not hashtags:
        print(f"✗ Champ 'hashtags' vide dans {post_dir / 'publication.json'} — rien à publier "
              f"sans hashtags (incident du 13/09/2026 : les 6 premiers posts sont partis sans "
              f"aucun hashtag, cf. Outillage-Publication-Instagram.md).", file=sys.stderr)
        sys.exit(1)

    caption = legende.rstrip("\n") + "\n.\n.\n.\n" + " ".join(hashtags)

    has_identity = (
        any(Path(name).stem.endswith(("-scene", "-titre")) for name in slides)
        or entry.get("identite") == "manuelle"
    )
    if not has_identity:
        print(f"✗ Aucune photo -scene ni -titre parmi 'slides', et pas de champ "
              f"'identite': 'manuelle' dans publication.json — publication refusée (ce post "
              f"n'a ni identité d'événement/titre issue de /masque-photos --serie, ni "
              f"confirmation manuelle qu'il s'agit d'un montage hors-série). Ajouter l'une "
              f"des deux avant de publier.", file=sys.stderr)
        sys.exit(1)

    repo_root = find_repo_root(post_dir)
    raw_base = github_raw_base_url(repo_root)

    photo_paths = []
    for name in slides:
        p = post_dir / "photos" / name
        if not p.exists():
            print(f"✗ Photo listée dans 'slides' introuvable : {p}", file=sys.stderr)
            sys.exit(1)
        photo_paths.append(p)

    image_urls = [image_url_for(p, repo_root, raw_base) for p in photo_paths]

    print(f"— {post_dir.name} — {len(image_urls)} image(s) — "
          f"{'CARROUSEL' if len(image_urls) > 1 else 'IMAGE UNIQUE'}")
    for url in image_urls:
        check_url_reachable(url)
        print(f"  ✓ accessible : {url}")

    ig_user_id = env_or_exit("IG_USER_ID")
    access_token = env_or_exit("META_ACCESS_TOKEN")

    if len(image_urls) == 1:
        container_id = create_image_container(ig_user_id, access_token, image_urls[0], caption=caption)
        wait_container_ready(container_id, access_token)
    else:
        child_ids = []
        for url in image_urls:
            cid = create_image_container(ig_user_id, access_token, url, is_carousel_item=True)
            wait_container_ready(cid, access_token)
            child_ids.append(cid)
        container_id = create_carousel_container(ig_user_id, access_token, child_ids, caption)
        wait_container_ready(container_id, access_token)

    print(f"✓ Conteneur prêt : {container_id}")

    if not args.publier:
        print("— dry-run : rien publié (relancer avec --publier pour publier réellement) —")
        return

    media_id = publish_container(ig_user_id, access_token, container_id)
    print(f"✓ Publié sur Instagram : media id {media_id}")

    entry["statut"] = "publie"
    entry["instagram_media_id"] = media_id
    (post_dir / "publication.json").write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n")
    print("✓ publication.json mis à jour (statut: publie)")


if __name__ == "__main__":
    main()
