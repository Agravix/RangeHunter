# 🔥 IP Scanner Pro

A fast and lightweight multi-threaded IP range scanner written in Python.

IP Scanner Pro reads CIDR ranges from a text file, expands them into individual hosts, scans a specified TCP port, and saves every reachable `IP:PORT` combination into an output file.

Designed to be simple, efficient, and capable of handling large IP ranges without loading every address into memory at once.

> Use this tool only on networks and systems you own or have explicit permission to scan.

---

## ✨ Features

* 🚀 Multi-threaded TCP port scanning
* 🌐 Supports CIDR ranges
* 📂 Reads multiple ranges from a text file
* ⚙️ Automatically adjusts worker count based on CPU cores
* 🧠 Memory-friendly queue system
* 📊 Real-time scan progress
* 🟢 Instantly displays discovered open ports
* 💾 Automatically saves results
* 🖥️ Works on Windows and Linux
* 🎨 Colored terminal interface
* ❌ Detects invalid CIDR entries
* 🔢 Supports TCP ports from `1` to `65535`

---

## 📋 Requirements

* Python 3.x
* `colorama` is recommended for colored terminal output
* `psutil` is optional and is used to automatically optimize the queue size based on available memory

Install the optional dependencies:

```bash
pip install colorama psutil
```

The scanner can still run without them because it contains fallback behavior.

---

## 📦 Installation

Clone the repository:

```bash
git clone https://github.com/Agravix/RangeHunter.git
```

Enter the project directory:

```bash
cd RangeHunter
```

Install dependencies:

```bash
pip install colorama psutil
```

---

## 📄 IP Range File

Create a text file such as:

```text
ranges.txt
```

Add one CIDR range per line:

```text
192.168.1.0/24
10.10.10.0/24
172.16.0.0/16
```

Empty lines are ignored.

Invalid CIDR ranges are reported and skipped.

---

## 🚀 Usage

Syntax:

```bash
python RH.py <ip_file> <port>
```

Example:

```bash
python RH.py ranges.txt 80
```

This scans port `80` across all usable hosts contained in the CIDR ranges from `ranges.txt`.

Another example:

```bash
python RH.py ranges.txt 443
```

This scans TCP port `443`.

---

## 🧪 Example

Input file:

```text
192.168.1.0/24
192.168.10.0/24
```

Run:

```bash
python RH.py ranges.txt 25565
```

Example output:

```text
[+] 192.168.1.25:25565 is OPEN
[+] 192.168.10.15:25565 is OPEN

Progress: [████████████████████████████████████████] 100.0%
```

---

## 💾 Output

Results are automatically saved using the following format:

```text
open_ports_<PORT>.txt
```

For example, when scanning port `25565`:

```text
open_ports_25565.txt
```

The file may contain:

```text
192.168.1.25:25565
192.168.10.15:25565
```

Results are written immediately when an open port is discovered, rather than waiting for the entire scan to finish.

---

## ⚙️ How It Works

The scanner reads each CIDR network from the supplied file and expands it using Python's `ipaddress` module.

It then places individual host addresses into a bounded queue.

Multiple worker threads retrieve addresses from the queue and attempt a TCP connection to the selected port.

A host is considered open when the TCP connection succeeds.

The program automatically calculates its worker count using the system CPU count:

```text
CPU Cores × 8
```

with a maximum of:

```text
200 workers
```

and a minimum of:

```text
20 workers
```

The default connection timeout is:

```text
1 second
```

---

## 📊 Scan Information

Before scanning starts, the tool displays information such as:

```text
Target Port
Total IPs to scan
Workers
Queue Size
Timeout
Operating System
Output File
```

During the scan, progress is periodically updated with:

```text
Progress
Scanned IPs
Open Ports Found
```

---

## ⚠️ Important

Scanning extremely large CIDR ranges can generate a very large number of connection attempts.

For example:

```text
/24  → around 254 usable IPv4 hosts
/16  → around 65,534 usable IPv4 hosts
/8   → over 16 million usable IPv4 hosts
```

Use appropriate ranges and make sure you have authorization before scanning external systems.

---

## 🛡️ Legal Disclaimer

This project is intended for:

* Network administration
* Authorized security testing
* Lab environments
* Educational purposes
* Testing infrastructure you own or are explicitly authorized to assess

The developer is not responsible for unauthorized or illegal use of this software.

Always obtain permission before scanning systems that you do not own.

---

## 🐍 Built With

* Python
* `socket`
* `ipaddress`
* `threading`
* `queue`
* `colorama`
* `psutil`

---

## 📜 License

You may add a license such as the MIT License if you want others to freely use, modify, and distribute the project.

---

## ⭐ Support

If you find this project useful, consider giving the repository a ⭐ on GitHub.
