"""Fetch the Real-POCQi public dataset (CC BY 4.0) from the Hugging Face Hub into ./data/.
Canonical source of the three parquet files used by every analysis script. Idempotent.
Usage: python3 fetch_data.py
If the hub layout differs, inspect the printed file list and adjust MAP below."""
import os, shutil
from huggingface_hub import hf_hub_download, list_repo_files

REPO="jjfenglab/Real-POCQi"
HERE=os.path.dirname(os.path.abspath(__file__))
DATA=os.path.join(HERE,'data'); os.makedirs(DATA,exist_ok=True)
# local canonical name -> substring to match in the hub file list
WANT={'questions.parquet':'question','answers.parquet':'answer','ratings.parquet':'rating'}

def main():
    files=[f for f in list_repo_files(REPO,repo_type='dataset') if f.endswith('.parquet')]
    print("parquet files in",REPO,":",files)
    for local,sub in WANT.items():
        match=next((f for f in files if sub in f.lower()),None)
        if not match:
            print(f"  [WARN] no hub file matches '{sub}' for {local}; skipping"); continue
        p=hf_hub_download(REPO,match,repo_type='dataset')
        dst=os.path.join(DATA,local); shutil.copy(p,dst)
        print(f"  {local:20s} <- {match}  ({os.path.getsize(dst)} bytes)")
    print("done. data/ ready.")

if __name__=="__main__": main()
