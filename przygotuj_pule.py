#!/usr/bin/env python3
"""Przygotowuje pule dla strony zbiórki (uruchamiać lokalnie, wynik commitować do Space'a).

  zdania_do_czytania.jsonl  - zdania ze śląskiej Wikipedii w pisowni Ślabikŏrza (CC BY-SA)
  tlumaczenia.jsonl         - polskie zdania z qa_seed_pl.jsonl + tłumaczenie Bielika na śląski

Przykład (z katalogu bielik-tokenizer):
    python3 zbiorka/przygotuj_pule.py --zdania 400 --adapter adapters-v3
    python3 zbiorka/przygotuj_pule.py --tylko-zdania      # bez modelu
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from prepare_szl_data import clean, orthography, read_wiki, template_kind, WIKI_JUNK  # noqa: E402

TU = Path(__file__).resolve().parent
DOZWOLONE = re.compile(r"^[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźżŌŎÔÃÕōŏôãõ ,.!?:;'\"„”–-]+$")
SKROT = re.compile(r"\b[A-ZŁŚŻ]\.|\b(tm|np|itp|r|ur|zm)\.")
ZDANIE = re.compile(r"(?<=[.!?])\s+(?=[A-ZŁŚŻŹĆŃÓŌŎÔÃÕ])")


def zdania_z_wiki(ile: int, artykuly: int, seed: int) -> list[dict]:
    widziane, wynik = set(), []
    for tekst in read_wiki("szl", limit=artykuly):
        for linia in tekst.split("\n"):
            if WIKI_JUNK.match(linia):
                continue
            for z in ZDANIE.split(clean(linia)):
                if not 40 <= len(z) <= 180 or not z[0].isupper() or z in widziane or not z.endswith((".", "!", "?")):
                    continue
                if orthography(z) != "slabikorz" or template_kind(z) or not DOZWOLONE.match(z) or SKROT.search(z):
                    continue
                widziane.add(z)
                wynik.append({"id": hashlib.sha1(z.encode()).hexdigest()[:10], "zdanie": z})
    random.Random(seed).shuffle(wynik)
    return wynik[:ile]


def tlumaczenia(model_dir: str, adapter: str, max_tokens: int) -> list[dict]:
    from bielik_przepisz_na_godke import INSTR, wyczysc
    from mlx_lm import generate, load
    from mlx_lm.sample_utils import make_sampler

    zdania = []
    for l in (ROOT / "qa_seed_pl.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            zdania += [r["q"], r["a"]]
    zdania = list(dict.fromkeys(z.strip() for z in zdania if len(z.strip()) >= 10))

    model, tok = load(str(ROOT / model_dir), adapter_path=str(ROOT / adapter))
    sampler = make_sampler(temp=0.3)
    wynik = []
    for i, pl in enumerate(zdania, 1):
        prompt = tok.apply_chat_template([{"role": "user", "content": INSTR + pl}], add_generation_prompt=True)
        szl = wyczysc(generate(model, tok, prompt=prompt, max_tokens=max_tokens, sampler=sampler, verbose=False))
        if szl and szl != pl:
            wynik.append({"id": hashlib.sha1(pl.encode()).hexdigest()[:10], "pl": pl, "bielik": szl})
        if i % 20 == 0:
            print(f"  {i}/{len(zdania)}  {pl[:40]} -> {szl[:40]}", flush=True)
    return wynik


def zapisz(path: Path, wiersze: list[dict]) -> None:
    path.write_text("".join(json.dumps(w, ensure_ascii=False) + "\n" for w in wiersze), encoding="utf-8")
    print(f"{path.name}: {len(wiersze)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zdania", type=int, default=400)
    ap.add_argument("--artykuly", type=int, default=30000, help="ile artykułów Wikipedii przejrzeć")
    ap.add_argument("--model", default="bielik-4.5b-mlx")
    ap.add_argument("--adapter", default="adapters-v3")
    ap.add_argument("--max-tokens", type=int, default=120)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tylko-zdania", action="store_true")
    a = ap.parse_args()

    zapisz(TU / "zdania_do_czytania.jsonl", zdania_z_wiki(a.zdania, a.artykuly, a.seed))
    if not a.tylko_zdania:
        zapisz(TU / "tlumaczenia.jsonl", tlumaczenia(a.model, a.adapter, a.max_tokens))


if __name__ == "__main__":
    main()
