# SKVOZNYAK · Qazline

Интерактивная сквозная аналитика Meta Ads × amoCRM.

- Публичная безопасная сборка: `docs/app/index.html`.
- Исходный шаблон: `src/v04.template.html`.
- Сборщик: `scripts/build_v04.py`.
- Проверки данных и приватности: `scripts/qa_v04.py`.
- Browser E2E: `scripts/e2e_v04.cjs`.

## Повторная сборка

```bash
python scripts/build_v04.py \
  --input-root /private/path/to/exports \
  --fx-json /private/path/to/usd_kzt_daily_2026-04-01_2026-10-12.json \
  --public-out docs/app/index.html \
  --private-out /private/path/skvoznyak_qazline_private_v04.html
```

Входные CSV/XLSX, FX-файл и private HTML не коммитятся. Публичный payload не содержит строк сделок, Deal ID, менеджеров или индивидуальных платежей. Выручка публикуется только для полных `Ad × Month` ячеек с не менее чем пятью подтверждёнными продажами и округляется до 10 000 ₸.

Текущий production URL: https://gilmiyaroff.github.io/SkvoznyakQL/app/
