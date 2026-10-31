# Zbiórka gŏdki

Strona do zbierania śląskiej gŏdki dla modelu Bielik: teksty, nagrania zdań
i poprawki tłumaczeń. Zgłoszenia trafiają do publicznego zbioru
[mosad2024/szl-godka-zbiorka](https://huggingface.co/datasets/mosad2024/szl-godka-zbiorka) (CC0).

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
- `dataset_card.md` — opis zbioru na HF
