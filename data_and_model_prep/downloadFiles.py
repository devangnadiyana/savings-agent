import datetime as dt
# Standard-library module for dates and times; "as dt" lets us write dt.date instead of datetime.date.
import json
# Standard-library module that turns Python lists and dicts into JSON text (used for the manifest file).
import time
# Standard-library module; we only use time.sleep() to pause between requests to the Bank of England.
from pathlib import Path
# Path objects represent file locations and join them with "/" correctly on both Windows and Mac.

import requests
# Third-party library for HTTP downloads (pip install requests). Kept in its own block because it isn't part of Python itself.

RAW = Path("data/raw")
# Root folder for every downloaded file. It's a relative path, so run the script from your project folder.
HEADERS = {"User-Agent": "savings-agent-data/0.1 (personal research project)"}
# Sent with every request so servers can see what is calling them; some sites reject requests that don't send one.
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
# Fixed English month abbreviations. The Bank of England wants dates like 01/Jan/1975, and strftime("%b") follows the computer's language, so it could produce "janv.".
IADB = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
# The Bank of England database's CSV download address (the same one the maintained open-source 'boe' R package uses).
BOE_MEDIA = "https://www.bankofengland.co.uk/-/media/boe/files/statistics"
# The common start of the Bank's direct file links (yield-curve zips, survey files), so the URLs below stay short.
ONS_CSV = "https://www.ons.gov.uk/generator?format=csv&uri=/economy/inflationandpriceindices/timeseries"
# The common start of the ONS "download as CSV" links; the series ID and dataset name are added below.

BOE_SERIES = {
    # Dictionary of Bank of England series code -> plain-English description. Each code is downloaded to its own CSV file.
    "IUDBEDR": "Bank Rate, daily",
    # The official Bank Rate on every working day since 1975: the anchor every other rate gets compared with.
    "IUMABEDR": "Bank Rate, monthly average",
    # The Bank's own monthly average of Bank Rate; used later to check our monthly numbers against theirs.
    "IUDSOIA": "SONIA overnight rate, daily",
    # SONIA, the overnight rate banks pay each other (from 1997); it tracks Bank Rate closely.
    "IUMB6VJ": "Advertised rate: instant access, incl. bonuses",
    # Average rate banks advertise on new instant-access accounts, counting introductory bonuses. Monthly.
    "IUMB6VK": "Advertised rate: instant access, excl. bonuses",
    # The same without bonuses: closer to what a saver earns once the bonus ends.
    "IUMB6VL": "Advertised rate: variable cash ISA, incl. bonuses",
    # Average advertised rate on new easy-access cash ISAs, with bonuses. The Bank changed its method for the ISA series in January 2016.
    "IUMB6VM": "Advertised rate: variable cash ISA, excl. bonuses",
    # The same without bonuses.
    "IUMB6VN": "Advertised rate: 1-year fixed cash ISA",
    # Average advertised rate on new 1-year fixed-rate cash ISAs.
    "IUMZID2": "UNCONFIRMED, probably advertised 2-year fixed cash ISA",
    # Code taken from the Bank's quoted-rates table; the titles file this script downloads will confirm what it is.
    "IUMWTFA": "UNCONFIRMED, probably advertised 1-year fixed bond",
    # Same: probably the 1-year fixed-rate bond, the core input to the fix-or-stay model.
    "IUMB6RH": "UNCONFIRMED, probably advertised 2-year fixed bond",
    # Same: probably the 2-year fixed-rate bond.
    "IUMB6RI": "UNCONFIRMED, probably advertised 3-year fixed bond",
    # Same: probably the 3-year fixed-rate bond.
    "CFMZ6IQ": "Rate earned: existing household sight deposits",
    # Average rate households actually earn on money already sitting in instant-access and current accounts.
    "CFMZ6IW": "Rate earned: existing household time deposits",
    # Average rate households earn on money already in fixed-term and notice accounts.
    "CFMZ6IH": "Rate earned: new household time deposits",
    # Average rate on fixed-term money newly deposited that month.
}

FILES = {
    # Dictionary of where to save each file (inside data/raw) -> the address it comes from.
    "boe/yield_curves/glcnominalmonthedata.zip": f"{BOE_MEDIA}/yield-curves/glcnominalmonthedata.zip",
    # Gilt (UK government bond) yield curve, month-end values back to 1979: market interest rates at every maturity.
    "boe/yield_curves/oismonthedata.zip": f"{BOE_MEDIA}/yield-curves/oismonthedata.zip",
    # OIS (swap) curve, month-end: the market's expected path for Bank Rate. Starts around 2009.
    "boe/yield_curves/glcnominalddata.zip": f"{BOE_MEDIA}/yield-curves/glcnominalddata.zip",
    # The gilt curve again, every working day: for the daily early-warning signal later.
    "boe/yield_curves/oisddata.zip": f"{BOE_MEDIA}/yield-curves/oisddata.zip",
    # The OIS curve, every working day.
    "boe/nmg/nmg_2004_2011.xlsx": f"{BOE_MEDIA}/research-datasets/boe-nmg-household-survey-data-2004-11.xlsx",
    # Bank of England/NMG household survey answers, 2004-2011 (7 MB).
    "boe/nmg/nmg_2011_2026.xlsx": f"{BOE_MEDIA}/research-datasets/boe-nmg-household-survey-data.xlsx",
    # The same survey, 2011-2026 (71 MB): thousands of households' answers about their finances.
    "ons/cpi_annual_rate_D7G7.csv": f"{ONS_CSV}/d7g7/mm23",
    # ONS consumer price inflation, annual rate (series D7G7): turns interest rates into real, after-inflation returns.
    "ons/cpi_index_D7BT.csv": f"{ONS_CSV}/d7bt/mm23",
    # ONS consumer price index level (series D7BT, 2015 = 100): for month-by-month inflation.
    "hmrc/isa_tables_2025.ods": "https://assets.publishing.service.gov.uk/media/68c94808c6df905ce7708427/Individual_Savings_Account_Tables_2025.ods",
    # HMRC's ISA statistics tables (September 2025 release): how much people put into ISAs, by type, income and age.
}


def boe_date(day: dt.date) -> str:
    # Turns a Python date into the Bank of England's format, e.g. date(2026, 10, 3) -> "03/Oct/2026".
    return f"{day.day:02d}/{MONTHS[day.month - 1]}/{day.year}"
    # {day.day:02d} = the day as 2 digits with a leading zero; MONTHS[day.month - 1] because months run 1-12 but tuple positions run 0-11.


def iadb_url(codes: str, start: dt.date, layout: str) -> str:
    # Builds the full download address for one or more series codes (comma-separated), from 'start' to today.
    return (f"{IADB}?csv.x=yes&Datefrom={boe_date(start)}&Dateto={boe_date(dt.date.today())}"
            # csv.x=yes asks for a CSV file instead of a web page; Datefrom and Dateto set the date range.
            f"&SeriesCodes={codes}&UsingCodes=Y&CSVF={layout}")
            # SeriesCodes = which series; CSVF=TN gives a plain table (header row: DATE plus the codes); CSVF=TT adds the series titles.


def looks_like_html(head: bytes) -> bool:
    # True if the first bytes of a download look like a web page (an error page) rather than data.
    return b"<html" in head[:2000].lower() or head.lstrip().startswith(b"<")
    # Looks for "<html" in the first 2,000 bytes (lower-cased), or checks whether the content starts with "<", which every HTML tag does.


def download(url: str, target: Path) -> int:
    # Downloads one address to 'target' safely and returns the file size in bytes; raises an error if the result isn't real data.
    target.parent.mkdir(parents=True, exist_ok=True)
    # Creates the destination folder and any missing parent folders; no error if they already exist.
    partial = target.with_name(target.name + ".part")
    # Temporary name such as IUDBEDR.csv.part: the file only gets its real name once it's complete and checked.
    with requests.get(url, headers=HEADERS, timeout=300, stream=True) as response:
        # Sends the HTTP GET request. stream=True downloads in pieces instead of holding a 71 MB file in memory; timeout=300 gives up after 5 minutes of silence; 'with' closes the connection afterwards.
        response.raise_for_status()
        # Raises an error for failure status codes such as 404 (not found) or 500 (server error).
        with partial.open("wb") as out:
            # Opens the temporary file for writing raw bytes ("wb" = write binary); 'with' closes it when the block ends.
            for chunk in response.iter_content(chunk_size=1 << 20):
                # Loops over the download in 1 MB pieces (1 << 20 = 2 to the power 20 = 1,048,576 bytes).
                out.write(chunk)
                # Appends each piece to the temporary file.
    with partial.open("rb") as saved:
        # Reopens the finished temporary file for reading bytes ("rb" = read binary).
        head = saved.read(2000)
        # Reads only the first 2,000 bytes: enough to recognise a web page or a zip file without loading the whole file.
    if looks_like_html(head):
        # The Bank sends error pages with status 200 ("OK"), so raise_for_status() can't catch them; this check can.
        partial.unlink()
        # Deletes the temporary file so no bad data is left lying around.
        raise ValueError("server sent a web page instead of data")
        # Stops this one download with a readable reason; main() catches it and moves on to the next file.
    if target.suffix in {".zip", ".xlsx", ".ods"} and not head.startswith(b"PK"):
        # .zip, .xlsx and .ods files are all zip archives inside, and every zip archive starts with the bytes "PK".
        partial.unlink()
        # Deletes the broken temporary file.
        raise ValueError("file is not a valid zip/xlsx/ods")
        # Reports the problem instead of saving a corrupt file under a real name.
    partial.replace(target)
    # Renames the checked temporary file to its real name in one step, replacing any older copy.
    return target.stat().st_size
    # Returns the file size in bytes so the summary can print it.


def check_boe_csv(path: Path, code: str) -> int:
    # Confirms a downloaded Bank of England CSV really contains the requested series; returns its number of data rows.
    lines = [line for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines() if line.strip()]
    # Reads the file as text ("utf-8-sig" drops an invisible byte-order mark if one is there), splits it into lines and keeps only the non-blank ones.
    if not lines or not lines[0].strip('"').startswith("DATE") or code not in lines[0]:
        # The first line must start with DATE (a leading quote mark is allowed) and contain the series code, e.g. "DATE,IUDBEDR".
        raise ValueError(f"unexpected first line: {lines[0][:80] if lines else 'empty file'!r}")
        # Shows the first 80 characters of what actually arrived; !r prints it with quotes so hidden characters become visible.
    return len(lines) - 1
    # Number of lines minus the header line = number of data rows.


def main() -> None:
    # Builds the list of downloads, runs them one by one, prints a summary and writes the manifest.
    jobs = [(f"boe/series/{code}.csv", iadb_url(code, dt.date(1975, 1, 1), "TN"), code) for code in BOE_SERIES]
    # One job per Bank of England series as (file name, address, code). Each is requested from 1975; the Bank returns whatever history exists.
    jobs.append(("boe/series_titles_raw.csv", iadb_url(",".join(BOE_SERIES), dt.date(2025, 1, 1), "TT"), None))
    # One extra request for all codes in the "with titles" layout, kept short (from 2025) because we only need the titles, to confirm what each code is.
    jobs += [(name, url, None) for name, url in FILES.items()]
    # Adds the direct file downloads; None means "not a Bank of England series, so skip the CSV check".

    manifest = []
    # Collects one record per download (what, from where, when, size, success or error); saved at the end.
    for name, url, code in jobs:
        # Unpacks each job into its three parts and processes the jobs in order.
        target = RAW / name
        # Full path where this file will be saved, e.g. data/raw/boe/series/IUDBEDR.csv.
        entry = {"file": name, "url": url, "downloaded_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        # Starts this file's record with a UTC timestamp such as 2026-10-19T08:45:12+00:00: where and when it came from.
        try:
            # Anything inside 'try' can fail; a failure jumps to 'except' instead of stopping the whole script.
            entry["bytes"] = download(url, target)
            # Downloads and checks the file, and records its size.
            if code:
                # Only Bank of England series have a code, so only they get the extra CSV check.
                entry["rows"] = check_boe_csv(target, code)
                # Confirms the CSV holds the right series and records how many rows it has.
                entry["description"] = BOE_SERIES[code]
                # Copies the plain-English description into the record.
            entry["ok"] = True
            # Marks this download as successful.
            detail = f"{entry['rows']:>7} rows" if code else f"{entry['bytes'] / 1e6:>7.1f} MB"
            # Summary detail: row count for series, size in MB for files; :>7 right-aligns it in 7 characters so the columns line up.
            print(f"OK    {name:<45} {detail}")
            # Prints one summary line; :<45 left-aligns the name in 45 characters.
        except Exception as error:
            # Catches any failure in this one download (network error, error page, broken file) and carries on with the rest.
            entry["ok"] = False
            # Marks this download as failed.
            entry["error"] = str(error)
            # Stores the reason in the record.
            print(f"FAIL  {name:<45} {error}")
            # Prints the failure and its reason.
        manifest.append(entry)
        # Adds this file's record to the manifest list.
        if url.startswith(IADB):
            # Only after requests to the Bank of England database:
            time.sleep(1)
            # wait one second before the next request, so we don't hammer their server.

    (RAW / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    # Saves every record to data/raw/manifest.json as readable JSON (indent=2 spreads it over several lines).
    failed = sum(not entry["ok"] for entry in manifest)
    # Counts the failures: 'not' turns each failed record's False into True, and True counts as 1 when summed.
    print(f"\n{len(manifest) - failed} of {len(manifest)} downloaded. Details: {RAW / 'manifest.json'}")
    # Final line: how many succeeded out of the total, and where the details are.


if __name__ == "__main__":
    # True only when this file is run directly (python download_all.py), not when another file imports it.
    main()
    # Starts the downloads.