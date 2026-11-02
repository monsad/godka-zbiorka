# Zbiórka gŏdki

Strona do zbierania śląskiej gŏdki dla modelu Bielik: teksty, nagrania zdań
i poprawki tłumaczeń. Zgłoszenia trafiają najpierw do prywatnej skrzynki
`mosad2024/szl-godka-zbiorka`; po sprawdzeniu publikujemy je w otwartym zbiorze
[mosad2024/szl-godka](https://huggingface.co/datasets/mosad2024/szl-godka) (CC0).

## Przegląd zgłoszeń

```bash
hf auth login                    # konto z zapisem do obu zbiorów
python przeglad.py               # t = tak, n = nie, p = pomiń, o = odtwórz nagranie, q = koniec
```

Zatwierdzone trafiają do zbioru publicznego, decyzje do `decyzje/` w skrzynce
(nic nie jest oceniane dwa razy).

Działa na darmowym Streamlit Community Cloud; dane wysyła co 2 minuty na Hugging Face.

## Lokalnie

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py   # bez HF_TOKEN zapisuje tylko do folderu dane/
python -m pytest tests           # testy zapisu, puli zdań i całej strony
```

## Wdrożenie (Streamlit Community Cloud)

1. https://share.streamlit.io → zaloguj przez GitHub → **Create app** → to repo, plik `streamlit_app.py`.
2. **Advanced settings → Secrets**:
   ```toml
   HF_TOKEN = "hf_..."   # token fine-grained: write tylko do mosad2024/szl-godka-zbiorka
   ```

## Pliki

- `streamlit_app.py` — strona
- `storage.py` — walidacja i zapis zgłoszeń
- `pule.py` — losowanie zdań i tłumaczeń
- `zdania_do_czytania.jsonl` — 400 zdań ze ślōnskij Wikipedyje (CC BY-SA)
- `tlumaczenia.jsonl` — 123 polskie zdania z tłumaczeniem Bielika do poprawy
- `przygotuj_pule.py` — odświeża obie pule (wymaga repo bielik-tokenizer i modelu MLX)
- `przeglad.py` — przegląd zgłoszeń: skrzynka → zbiór publiczny
- `dataset_card.md` — opis zbioru publicznego, `dataset_card_skrzynka.md` — opis prywatnej skrzynki
