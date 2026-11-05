#!/usr/bin/env python3
"""Fetch Hanyoung Foreign Language High School dinner menus from the NEIS API."""

import calendar
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
ATPT_OFCDC_SC_CODE = "B10"
# This is the school code currently configured in index.html.
SD_SCHUL_CODE = "7010259"
MEAL_CODE = "3"  # Dinner


def month_range():
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    start = now.replace(day=1)
    # Include this month and the following two months for calendar navigation.
    end_year = now.year
    end_month = now.month + 2
    while end_month > 12:
        end_year += 1
        end_month -= 12
    end_day = calendar.monthrange(end_year, end_month)[1]
    end = now.replace(year=end_year, month=end_month, day=end_day)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def fetch_rows(api_key, start_date, end_date):
    params = {
        "KEY": api_key,
        "Type": "json",
        "pIndex": "1",
        "pSize": "1000",
        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": SD_SCHUL_CODE,
        "MMEAL_SC_CODE": MEAL_CODE,
        "MLSV_FROM_YMD": start_date,
        "MLSV_TO_YMD": end_date,
    }
    request = Request(
        API_URL + "?" + urlencode(params),
        headers={"User-Agent": "HYFL-Dinner-Menu-Updater/1.0"},
    )
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    result = payload.get("RESULT")
    if result:
        code = result.get("CODE", "")
        if code == "INFO-200":
            return []
        if code != "INFO-000":
            raise RuntimeError(
                f"NEIS API returned {code}: {result.get('MESSAGE', 'unknown error')}"
            )

    blocks = payload.get("mealServiceDietInfo", [])
    for block in blocks:
        if isinstance(block, dict) and "row" in block:
            return block["row"] or []
    return []


def main():
    api_key = os.environ.get("NEIS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "NEIS_API_KEY is missing. Add it in GitHub repository Settings > "
            "Secrets and variables > Actions."
        )

    start_date, end_date = month_range()
    rows = fetch_rows(api_key, start_date, end_date)
    rows.sort(key=lambda row: row.get("MLSV_YMD", ""))

    output = {
        "updatedAt": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
        "period": {"from": start_date, "to": end_date},
        "rows": rows,
    }
    target = Path("meals.json")
    target.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Saved {len(rows)} dinner records to {target} ({start_date}–{end_date}).")


if __name__ == "__main__":
    main()
