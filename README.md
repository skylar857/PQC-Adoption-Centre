 PQC Adoption Scanner

Which websites are already ready for quantum computers?

A small measurement study of *hybrid post-quantum key exchange* (X25519MLKEM768) in HTTPS. I scanned 304 servers: the global top sites, plus hand-picked Indian government, university and bank/fintech sites. For each one I recorded whether it already uses the new quantum-resistant handshake, and I tried to work out why some do and some don't.

Live site: *[add your Vercel link here]*


 Why I built this

I study electronics (VLSI), and cryptography is what I wanted to understand properly. Reading about post-quantum cryptography only got me so far, so I decided to measure something real: how far has the move to quantum-resistant encryption actually reached on the live internet? Building the tool taught me more than the reading did, and this README is mostly about that.



 What I learnt

 1. What encryption on the web is really doing

When you open an HTTPS website, your browser and the server first have to agree on a secret key. The problem is that they do it over the open internet, where anyone can listen in. Once both sides hold the same secret, they use fast "symmetric" encryption (like AES) for everything else. The hard part is **agreeing on the secret without anyone else learning it**. That step is called *key exchange*, and it is what my project looks at.

A way I picture it is mixing paint. You and the server each pick a private colour and share one public colour. Each of you mixes your private colour into the public one and sends the result across. Then you mix your own private colour in again. You both end up with exactly the same final colour, but someone watching only saw mixtures, and un-mixing paint is practically impossible. Real key exchange does this with maths instead of paint. **X25519**, the classical method in my scans, is a version of this idea built on elliptic curves.

 2. Why quantum computers are a problem

Today's key exchange (and RSA, and the elliptic curves behind X25519) relies on maths puzzles that are very hard for normal computers. A large enough quantum computer running *Shor's algorithm* could solve those puzzles quickly. Symmetric encryption like AES is hurt much less and can be fixed with longer keys. As far as I know, no publicly known quantum computer is big enough yet, so this is about preparing early.

3. "Harvest now, decrypt later"

This is why the migration cannot wait. Someone can record encrypted traffic today, store it, and decrypt it years later once a quantum computer exists. Anything that must stay secret for a long time is already at risk. This is also why **key exchange moves first**. Certificates and signatures (the proof of *who* you are talking to) only matter at the moment of the connection, so an attacker would need the quantum computer right then. They can migrate later. This project therefore looks only at key exchange.

 4. The new tool: ML-KEM

NIST standardised **ML-KEM** (earlier called Kyber) in 2024. A KEM works like a locked box. One side makes a key pair and shares the public half. The other side puts a fresh random secret inside a small package that only the owner of the private half can open, and sends it back. Both now share a secret. The security rests on *lattice* problems, which you can think of as finding a hidden point in a huge grid of slightly blurred points. No fast quantum method for that is known.

 5. Why "hybrid"

Because ML-KEM is still new, nobody wants to bet everything on it. **X25519MLKEM768** runs the classical X25519 and ML-KEM-768 together and combines both secrets. An attacker has to break both. This protects against two risks at once: a future quantum computer, and an unexpected flaw in the new algorithm.

The cost is size, not speed:

| | Client sends | Server sends |
|---|---|---|
| X25519 | 32 bytes | 32 bytes |
| ML-KEM-768 | 1,184 bytes | 1,088 bytes |
| Hybrid X25519MLKEM768 | 1,216 bytes | 1,120 bytes |

6. How my scanner works

For each server, I make one normal TLS 1.3 connection with OpenSSL 3.5. I offer the hybrid group first and plain X25519 as a fallback, then read which one the server picked. If the connection fails, extra checks tell apart a server that really does not support something from one that simply did not answer. Each host ends up in one category: hybrid PQC, classical only, TLS 1.2 only, or unreachable. To find out *who* serves each site, I send one plain `GET /` request and look for identifying response headers (Cloudflare, CloudFront, Akamai and so on).

7. Lessons from building it

- A tool you have not checked will lie to you.** My first version labelled some normal servers as "no TLS 1.3" because OpenSSL prints classical and hybrid results in different formats and my code only read one of them. I only caught it by comparing the output with a manual `openssl s_client` run.
- "Did not answer" is not "does not support".** Some hosts timed out on every test, including plain TLS 1.2. Counting them as "no TLS 1.3" would have distorted the percentages, so the scanner now treats them as unreachable and leaves them out of the denominator.
- Do not trust data you typed from memory.** Several hostnames I added did not exist, and a DNS check caught them.
- Small samples are noisy.** When I grew the Indian samples from about 16 to about 50 hosts per group, the numbers shrank and the confidence intervals tightened. Reporting the interval next to every percentage is the honest way to show that.
- A pattern is not an explanation.** Hybrid support turned out to be closely tied to who hosts the site (see below), but I only observed that link and did not test the cause.



 Results

Scan of 22 November 2026, run from Chennai, India. "Reachable" excludes hosts that did not answer. CI is a 95% confidence interval.

| Group | Reachable | Hybrid PQC | Adoption | 95% CI |
|---|---|---|---|---|
| Overall | 264 | 137 | 51.9% | 45.9-57.9% |
| Global top sites | 118 | 70 | 59.3% | 50.3-67.8% |
| Indian banks / fintech | 47 | 32 | 68.1% | 53.8-79.6% |
| Indian government | 49 | 26 | 53.1% | 39.4-66.3% |
| Indian universities | 50 | 9 | 18.0% | 9.8-30.8% |

What the data supports:

- About half of the reachable hosts already negotiate the hybrid exchange.
- Universities had the lowest adoption, and their interval does not overlap with any other group. Banks, government and global sites cannot be ranked against each other because their intervals overlap.
- Every one of the 72 hosts identified behind six major edge providers (Cloudflare, CloudFront, Akamai, Google, Meta, Fastly) negotiated hybrid PQC. Among the remaining 192 hosts, adoption was about 34%.
- No reachable university host was identified behind those six providers, but 48 of the 50 could not be attributed to any provider, so I cannot say universities "do not use CDNs".

 Benchmark

Measured with `openssl speed` (OpenSSL 3.5.9, AMD Ryzen 7 7840U, Docker on WSL2, median of 3 runs):

| Operation | Time |
|---|---|
| ML-KEM-768 key generation | about 47.7 µs |
| ML-KEM-768 encapsulation | about 37.6 µs |
| ML-KEM-768 decapsulation | about 56.4 µs |
| X25519 scalar multiplication | about 24.9 µs |

Estimated extra CPU per handshake for the hybrid: about 104 µs on the client and 38 µs on the server. These are estimates built from the numbers above, not full-handshake timings. Next to network delay this is tiny, so the practical cost of hybrid is the extra bytes sent.



 Limitations

- The hosts are **hand-selected**, not a random sample, so the results describe this sample and not "Indian websites" in general.
- One snapshot, from one location. Results can differ by time and vantage point.
- This measures what **servers** accept, not what browsers send.
- Only the key exchange is hybrid. Certificates and signatures are still classical.
- Many sites get hybrid support from a CDN in front of them, so a hybrid result does not always mean the site operator enabled it.
- Provider attribution from HTTP headers is a **lower bound**, because many sites hide identifying headers.
- The Tranco top list includes some infrastructure domains that are not websites, and a few Indian hosts answered only intermittently.
- Handshake CPU costs are estimates.

Ethics: one TLS handshake and one `GET /` request per host, with a timeout. No port scanning, no repeated probing, no login attempts.



 How to reproduce

You need Docker, Python 3.11+ and Git.


docker build -t pqc-scanner .

 1. Download the Tranco top-1M list from tranco-list.eu and save it as data/tranco.csv
python scanner/build_domains.py

 2. Scan (needs OpenSSL 3.5+, provided by the Docker image)
docker run --rm -v "${PWD}:/app" pqc-scanner python3 scanner/scanner_pqc.py data/domains.csv data/results.csv

 3. Analyse and attribute providers
python analysis/analysis.py
python analysis/providers.py

 4. Benchmark
docker run --rm -v "${PWD}:/app" pqc-scanner python3 benchmark/bench.py


Then open the project folder with a local server (for example the VS Code Live Server extension). The landing page is `index.html` and the full interactive study is in `site/`.

 Repository layout


scanner/     scan script, domain list builder, recheck helper
analysis/    adoption statistics and provider attribution
benchmark/   ML-KEM vs X25519 timing script
data/        host lists and scan results (Tranco list not included)
dashboard/   JSON outputs read by the website
site/        interactive study (HTML, CSS, JavaScript, Three.js)
index.html   landing page
 
 Plain-language glossary

- Key exchange: two parties agreeing on a shared secret over an open channel.
- TLS: the protocol behind HTTPS. TLS 1.3 is the current version.
- X25519: today's common key exchange, based on elliptic curves.
- ML-KEM: the new NIST-standard quantum-resistant key exchange.
- Hybrid: using the classical and the quantum-resistant method together.
- CDN / edge provider: a company (like Cloudflare) that sits in front of websites and serves them.
- Confidence interval: the range where the true value probably lies, given the sample size.
