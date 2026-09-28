# MOEX Analytics Platform

Учебно-практический проект аналитической платформы для сбора,
хранения и последующего анализа данных российского финансового рынка.

Платформа получает данные из MOEX ISS, API Банка России и T-Invest,
преобразует их через Python ETL и загружает в PostgreSQL DWH.

> **Текущий статус:** реализованы источники данных, ETL-слой и DWH.
> Следующие этапы — аналитические MART-таблицы и визуализация в Apache Superset.

## Текущий стек

- Python
- PostgreSQL 17
- Docker Engine
- Docker Compose
- DBeaver
- Git и GitHub

## Архитектура

MOEX ISS ─┐
CBR API  ─┼──> Python ETL ──> PostgreSQL DWH ──> MART ──> Superset
T-Invest ─┘

## Источники исходных данных

| Source         | Data                                                               |
|----------------|--------------------------------------------------------------------|
| MOEX ISS       | акции, индексы, дневная история, минутные свечи, сплиты, состав индексов |
| Bank of Russia | валюты, валютные курсы, ключевая ставка                            |
| T-Invest       | идентификаторы инструментов и дивидендные события                  |


### MOEX ISS:
https://iss.moex.com/iss/reference/
https://moexapi.tech-order.ru/all_companies

### Bank of Russia
https://www.cbr.ru/statistics/data-service/APIdocumentation/
https://www.cbr.ru/DailyInfoWebServ/DailyInfo.asmx?op=KeyRateXML
https://www.cbr.ru/development/sxml/

### T-Invest
https://developer.tbank.ru/invest/api


## DWH

В PostgreSQL используется схема `dwh`.

| Table | Purpose |
|---|---|
| `security` | справочник акций |
| `index` | справочник индексов |
| `calendar` | календарный справочник |
| `currency` | справочник валют |
| `security_daily` | дневная история акций |
| `index_daily` | дневная история индексов |
| `candle_1m` | минутные свечи акций и индексов |
| `dividend` | дивидендные события |
| `split` | сплиты акций |
| `index_composition` | история состава индексов |
| `currency_rate` | валютные курсы |
| `key_rate` | ключевая ставка Банка России |

## ETL

ETL реализован на Python.

Основные свойства загрузки:

- получение данных из REST/XML API;
- retry для временных HTTP-ошибок;
- пагинация MOEX ISS;
- преобразование исходных данных к модели DWH;
- параметризованные SQL-запросы;
- идемпотентная загрузка через `UPSERT`;
- инкрементальная загрузка исторических данных там, где она оправдана;
- полный reload небольших наборов данных там, где дополнительная
  инкрементальная логика не даёт практической выгоды;
- централизованное логирование;
- конфигурация scope проекта отдельно от секретов.
