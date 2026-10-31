"""Zbiórka gŏdki: strona, przez którą ludzie przysyłają śląskie teksty, nagrania i poprawki tłumaczeń.

Zgłoszenia trafiają do lokalnego folderu `dane/`. Gdy jest ustawiony HF_TOKEN (sekret w Streamlit
albo zmienna środowiskowa), CommitScheduler co 2 minuty wysyła folder do publicznego zbioru.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

import streamlit as st

from pule import Pula
from storage import BladZgloszenia, Zbior, wav_do_numpy

TU = Path(__file__).resolve().parent


def _sekret(nazwa: str, domyslna: str | None = None) -> str | None:
    try:
        if nazwa in st.secrets:
            return st.secrets[nazwa]
    except FileNotFoundError:
        pass
    return os.environ.get(nazwa, domyslna)


DATASET_REPO = _sekret("DATASET_REPO", "mosad2024/szl-godka-zbiorka")


@st.cache_resource
def zasoby():
    """Raz na cały proces (wspólne dla wszystkich odwiedzających)."""
    folder = TU / "dane"
    folder.mkdir(exist_ok=True)
    token = _sekret("HF_TOKEN")
    if token:
        from huggingface_hub import CommitScheduler

        scheduler = CommitScheduler(repo_id=DATASET_REPO, repo_type="dataset", folder_path=folder,
                                    path_in_repo="data", every=2, token=token)
        lock = scheduler.lock
    else:
        lock = threading.Lock()   # lokalnie: tylko zapis do folderu
    return (Zbior(folder, lock), Pula.z_pliku(TU / "zdania_do_czytania.jsonl"),
            Pula.z_pliku(TU / "tlumaczenia.jsonl"))


zbior, zdania, tlumaczenia = zasoby()
ss = st.session_state
ss.setdefault("zdanie", zdania.losuj())
ss.setdefault("tl", tlumaczenia.losuj())
ss.setdefault("nr_nagrania", 0)      # zmiana klucza czyści widżet nagrywania


def wyslij(funkcja, *args) -> bool:
    try:
        funkcja(*args)
    except BladZgloszenia as e:
        st.error(str(e))
        return False
    ss.zapisane = True
    return True


def nowe_zdanie():
    ss.zdanie = zdania.losuj(ss.zdanie["id"] if ss.zdanie else None)
    ss.nr_nagrania += 1


def nowe_tlumaczenie():
    ss.tl = tlumaczenia.losuj(ss.tl["id"] if ss.tl else None)
    ss.pop("poprawka", None)


st.set_page_config(page_title="Zbiórka gŏdki", page_icon="🎙️")
if ss.pop("zapisane", False):
    st.toast("Dziynkujymy! Zapisane.", icon="✅")
st.title("Zbiórka gŏdki")
st.markdown(f"""
Pomōż nauczyć model językowy **Bielik** gŏdać po ślōnsku: napisz coś po śląsku,
przeczytaj zdanie na głos albo popraw tłumaczenie Bielika.

- Nie zbieramy imion, maili ani adresów — tylko to, co wpiszesz lub nagrasz.
- Wszystko trafia do **publicznego** zbioru
  [{DATASET_REPO}](https://huggingface.co/datasets/{DATASET_REPO}) na licencji **CC0**
  (domena publiczna) — każdy może z tego korzystać, także do trenowania modeli.
- Nie wpisuj danych osobowych (swoich ani cudzych).
""")

miejscowosc = st.text_input("Skąd jesteś? (opcjonalnie, np. Ruda Śląska)", max_chars=100)
zgoda = st.checkbox("Zgadzam się udostępnić to, co wyślę, na licencji CC0 (domena publiczna).")

tab_tekst, tab_glos, tab_popr = st.tabs(["✍️ Napisz po śląsku", "🎙️ Przeczytaj na głos", "🛠️ Popraw tłumaczenie"])

with tab_tekst:
    with st.form("tekst", clear_on_submit=True):
        st.markdown("Napisz cokolwiek po śląsku: wspomnienie, przepis, rozmowę, opowieść. "
                    "Pisz tak, jak gŏdŏsz — dowolną pisownią.")
        tekst = st.text_area("Twój tekst", height=200, max_chars=5000)
        if st.form_submit_button("Wyślij tekst", type="primary"):
            wyslij(zbior.zapisz_tekst, tekst, miejscowosc, zgoda)

with tab_glos:
    st.markdown("Przeczytaj zdanie na głos, tak jak gŏdŏsz na co dzień (1–30 sekund). "
                "Zdania pochodzą ze ślōnskij Wikipedyje (CC BY-SA).")
    if ss.zdanie:
        st.subheader(ss.zdanie["zdanie"])
        nagranie = st.audio_input("Nagraj", key=f"nagranie-{ss.nr_nagrania}")
        c1, c2 = st.columns(2)
        c1.button("Inne zdanie", on_click=nowe_zdanie, key="inne_zdanie")
        if c2.button("Wyślij nagranie", type="primary"):
            if nagranie is None:
                st.error("Najpierw nagraj zdanie.")
            else:
                try:
                    audio = wav_do_numpy(nagranie.getvalue())
                except BladZgloszenia as e:
                    st.error(str(e))
                else:
                    if wyslij(zbior.zapisz_nagranie, audio, ss.zdanie["id"], ss.zdanie["zdanie"],
                              miejscowosc, zgoda):
                        nowe_zdanie()
                        st.rerun()
    else:
        st.info("Brak zdań do przeczytania.")

with tab_popr:
    st.markdown("Bielik przetłumaczył zdanie na śląski. Popraw je tak, jak byś to naprawdę powiedział(a). "
                "Jeśli jest dobrze — wyślij bez zmian.")
    if ss.tl:
        st.markdown(f"**Po polsku:** {ss.tl['pl']}")
        poprawka = st.text_area("Po śląsku (popraw)", value=ss.tl["bielik"], height=100,
                                max_chars=5000, key="poprawka")
        c1, c2 = st.columns(2)
        c1.button("Inne zdanie", on_click=nowe_tlumaczenie, key="inne_tl")
        if c2.button("Wyślij poprawkę", type="primary"):
            if wyslij(zbior.zapisz_poprawke, ss.tl["pl"], ss.tl["bielik"], poprawka, miejscowosc, zgoda):
                nowe_tlumaczenie()
                st.rerun()
    else:
        st.info("Brak tłumaczeń do poprawienia.")
