# Повторная сборка и необходимые поля

## Required for exact attribution

- Meta: `ID рекламы` как исходная текстовая строка, account/campaign/adset IDs и `Дата начала отчетности`.
- CRM: стабильный `ID` сделки, полный `FB ad id`, `FB CTWA`, `Дата создания`.
- Qualification: `Квалифицированный`; дата изменения нужна для исторического qualification-event анализа.
- Payments: суммы и реальные даты полной оплаты/предоплаты плюс подтверждающий статус.
- Exact CAC: стабильный Contact/Customer ID и признак первой оплаченной покупки клиента.
- Actual ad stop: status history/API event; отсутствие расхода не заменяет это поле.
- Period reach: Meta API/экспорт на grain выбранного периода.

## Rebuild

1. Положить новые Meta CSV и amoCRM XLSX в приватную директорию; не копировать их в Git.
2. Проверить, что Meta Ad IDs остаются строками и имеют 18 цифр.
3. Обновить дневной FX JSON для всех report dates.
4. Запустить команду из README для одновременной public/private сборки.
5. Выполнить `qa_v04.py` и browser E2E.
6. Публиковать только `docs/app/index.html`; private HTML хранить в закрытом Google Drive.

Сборщик останавливается при повреждённом Ad ID, дублированном `Account + Ad + Date` или отсутствующем FX-дне. Candidate matching не используется.
