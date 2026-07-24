import urllib.request
import shutil
import tempfile
from pathlib import Path

def fetch_data_urls(index_url: str, base_url: str) -> list[str]:
    """Find all buoy data from the IABP website."""
    with urllib.request.urlopen(index_url) as resp:
        text = resp.read().decode()
    #print("scrape-buoy: done decoding")
    return [
        f"{base_url}/{line.split(';')[0]}.dat"
        for line in text.splitlines()
        if line.strip()
    ]

def download_all(urls: list[str], dest: Path) -> None:
    """Download all data by ID from the IABP website."""
    #print("scrape-buoy: starting download")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for url in urls:
            name = url.rsplit("/", 1)[-1]
            target = tmp_path / name
            #print(f"scrape-buoy: downloading {name}")
            with urllib.request.urlopen(url) as resp, target.open("wb") as f:
                shutil.copyfileobj(resp, f)
            #print("scrape-buoy: download complete")
        dest.mkdir(parents=True, exist_ok=True)
        for item in tmp_path.iterdir():
            #print(f"scrape-buoy: moving {item.name}")
            shutil.move(str(item), dest / item.name)
            #print("scrape-buoy: move complete")
    #print("scrape-buoy: all files downloaded!")

def fetch_buoy() -> None:
    """Fetch all raw buoy data from the IABP website."""
    pass
    # they might change this, which is why it's a function
    # urls = fetch_data_urls(
    #     "https://iabp.apl.uw.edu/TABLES/ArcticTable_Current.txt",
    #     "https://iabp.apl.uw.edu/WebData/"
    # )
    #download_all(urls, output_dir)
