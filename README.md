<div align="center">
<img alt="Identixia" src="https://raw.githubusercontent.com/identixia-IDV/identixia-assets/main/brand/logo.png" width="320"/>

<a href="https://identixia.com"><img src="https://img.shields.io/badge/Website-0F766E?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Website" /></a>
<a href="https://docs.identixia.com"><img src="https://img.shields.io/badge/Docs-0F766E?style=for-the-badge&logo=gitbook&logoColor=white" alt="Docs" /></a>
<a href="https://huggingface.co/Identixia"><img src="https://img.shields.io/badge/HuggingFace-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black" alt="Hugging Face" /></a>
<a href="https://hub.docker.com/u/identixia"><img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Hub" /></a>
<a href="https://playground.identixia.com/"><img src="https://img.shields.io/badge/Playground-0F766E?style=for-the-badge&logo=cloudplayground&logoColor=white" alt="Playground" /></a>
</div>

<div align="center">

# <img src="https://cdn.simpleicons.org/docker/2496ED" width="32" height="32" alt="" /> ID Document Liveness Detection SDK for Linux / Docker — HTTP API Demo | Identixia

</div>

Integrate **document liveness detection and anti-spoofing** with the **Identixia Linux / Docker SDK**. This repository provides a self-hosted Linux / Docker HTTP API for checking ID documents for presentation attacks such as screen replays, printed copies, and replaced photos. Document presentation attack detection (PAD) adds an authenticity check to identity verification workflows. This liveness-only sample does not include OCR or MRZ text extraction.

Use the sample to add document anti-spoofing checks to customer onboarding and Know Your Customer (KYC) workflows alongside a separate document recognition service. Processing runs on your own server; images are not sent to the Identixia cloud.

Image: [`identixia/document-liveness`](https://hub.docker.com/r/identixia/document-liveness).

<p><img src="https://img.shields.io/badge/Document%20PAD-0F766E?style=flat-square" alt="Document%20PAD" /> <img src="https://img.shields.io/badge/Authenticity-0F766E?style=flat-square" alt="Authenticity" /> <img src="https://img.shields.io/badge/API%208086-0F766E?style=flat-square" alt="API%208086" /> <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square" alt="Docker" /> <img src="https://img.shields.io/badge/KYC%20%2F%20eKYC-5A6573?style=flat-square" alt="KYC%20%2F%20eKYC" /></p>

> For setup, integration, and API guides, see the [ID Document Liveness Detection SDK documentation for Linux / Docker](https://docs.identixia.com/developers/id-document-sdk/liveness-linux-docker). This page covers the sample repository.

## <img src="https://api.iconify.design/lucide/clipboard-list.svg?color=%230F766E" width="24" height="24" alt="" /> SDK overview

Start the server and request its machine code using `GET /api/machinecode`. Send that code to [contact@identixia.com](mailto:contact@identixia.com) to request a license for this machine. Apply the returned key using the activation instructions below.

| Topic | Basic information |
| --- | --- |
| **Product** | On-premise **document liveness / authenticity** API (KYC / eKYC) |
| **Documents** | ID document presentation-attack detection (screen / print / photo-swap) |
| **What you run** | HTTP API on port **14107** |
| **Machine code** | `GET /api/machinecode` prints `data.machinecode`. Please contact us with that machine code to get a license. |
| **Activate** | Set `LICENSE=` in `.env`, or `POST /api/activate` with the key (saved into `.env`). |
| **Check status** | `GET /api/health` and `GET /api/licenseStatus` after activate |
| **Runtime** | Included in the Docker image |
| **Tools** | Linux x64 with Docker |
| **Privacy** | Authenticity checks stay in your VPC — no Identixia cloud |

---

## <img src="https://api.iconify.design/lucide/package.svg?color=%230F766E" width="24" height="24" alt="" /> SDK installation

Download [`documentliveness.zip`](https://github.com/identixia-IDV/ID-Document-Liveness-Detection-Docker/releases/tag/runtime) from this repository’s [Releases](https://github.com/identixia-IDV/ID-Document-Liveness-Detection-Docker/releases/tag/runtime). Unzip it into `lib/cpu/`. The files should sit in that folder, not inside an extra directory.

---

## <img src="https://api.iconify.design/lucide/terminal.svg?color=%230F766E" width="24" height="24" alt="" /> Quick start

### <img src="https://img.shields.io/badge/-1-0F766E?style=for-the-badge" alt="" /> Run the server

```bash
docker pull identixia/document-liveness:latest
docker run -d --name identixia-document-liveness \
  --shm-size=2gb --privileged \
  -p 14107:14107 \
  -v /etc/machine-id:/etc/machine-id:ro \
  identixia/document-liveness:latest
```
Copy `.env.example` to `.env` and edit the settings for your installation: `PORT`, `LICENSE`, `API_BASE`, and `DEMO_PORT`. Values set in the shell or in Compose’s `environment:` section take precedence over values in `.env`.

### <img src="https://img.shields.io/badge/-2-0F766E?style=for-the-badge" alt="" /> Get a license

```bash
curl -s http://127.0.0.1:14107/api/machinecode
```

The JSON response contains your machine code in `data.machinecode`. This value identifies the machine for licensing.

Email the machine code and the product you want to use to [contact@identixia.com](mailto:contact@identixia.com) to request a license key.

### <img src="https://img.shields.io/badge/-3-0F766E?style=for-the-badge" alt="" /> Activate / license

1. Email the machine code from the previous step, and the product name, to [contact@identixia.com](mailto:contact@identixia.com).
2. Put the key you receive in `.env` at the repository root: `LICENSE=YOUR_KEY`.
3. Restart the server, or send the key with the command below. Then continue with the next step.

```bash
curl -s -X POST http://127.0.0.1:14107/api/activate -H "Content-Type: application/json" -d "{\"license\":\"YOUR_KEY\"}"
```

### <img src="https://img.shields.io/badge/-4-0F766E?style=for-the-badge" alt="" /> Check that it is running

```bash
curl -s http://127.0.0.1:14107/api/health
```

### <img src="https://img.shields.io/badge/-5-0F766E?style=for-the-badge" alt="" /> Run document liveness

Replace `BASE64_JPEG` with a base64-encoded JPEG of the document.

```bash
curl -s -X POST http://127.0.0.1:14107/api/document/liveness -H "Content-Type: application/json" -d "{\"images\":[{\"image\":\"BASE64_FRONT\",\"page_idx\":0},{\"image\":\"BASE64_BACK\",\"page_idx\":1}]}"
```

### <img src="https://img.shields.io/badge/-6-0F766E?style=for-the-badge" alt="" /> Open the Gradio demo

Gradio runs on your computer, not inside the container. Clone this repository, keep the API running, then open a second terminal in the repository folder.

```bash
pip3 install -r requirements-demo.txt
python3 run_demo.py
```

Open http://127.0.0.1:14207

---

## <img src="https://api.iconify.design/lucide/list-checks.svg?color=%230F766E" width="24" height="24" alt="" /> Features

| Capability | Notes |
| --- | --- |
| Document liveness / authenticity | Presentation-attack signals for ID images |
| KYC / eKYC gate | Reject spoofed documents before trusting OCR fields |
| HTTP API | Default port **14107** |
| Gradio demo | Port **14207** |
| Postman | `postman/DocumentLiveness-API.postman_collection.json` |

---

## <img src="https://api.iconify.design/lucide/pc-case.svg?color=%230F766E" width="24" height="24" alt="" /> System requirements

| | |
| --- | --- |
| Host | Linux x64 with Docker |
| Ports | API **14107**, Gradio **14207** |
| Licensing | Bind-mount `/etc/machine-id` for stable machine codes |

---

## <img src="https://api.iconify.design/lucide/app-window.svg?color=%230F766E" width="24" height="24" alt="" /> Gradio demo

Gradio runs on your computer, not inside the container. Clone this repository, keep the API running, then open a second terminal in the repository folder.

```bash
pip3 install -r requirements-demo.txt
python3 run_demo.py
```

Open http://127.0.0.1:14207

## <img src="https://api.iconify.design/lucide/link.svg?color=%230F766E" width="24" height="24" alt="" /> Related

Full OCR product: [ID-Document-Recognition-Liveness-Detection-Docker](https://github.com/identixia-IDV/ID-Document-Recognition-Liveness-Detection-Docker) · Hub: [ID-Document-Recognition-Liveness-Detection-SDK](https://github.com/identixia-IDV/ID-Document-Recognition-Liveness-Detection-SDK)

## <img src="https://api.iconify.design/lucide/braces.svg?color=%230F766E" width="24" height="24" alt="" /> API

HTTP API on port **14107**. For image-processing requests, encode the JPEG image as base64 and include it in the JSON request body.

| Call | Route |
| --- | --- |
| Health | `GET /api/health` |
| Machine code | `GET /api/machinecode` |
| Activate | `POST /api/activate` with a JSON body containing your license key: `{"license":"YOUR_KEY"}` |
| Process | `POST /api/document/liveness` |

Send the document image. This build does not extract MRZ or barcodes.

```bash
curl -s http://127.0.0.1:14107/api/health
```

---

## <img src="https://api.iconify.design/lucide/mail.svg?color=%230F766E" width="24" height="24" alt="" /> Contact

<div align="center">

<a href="mailto:contact@identixia.com"><img alt="Email contact@identixia.com" src="https://img.shields.io/badge/Email-contact%40identixia.com-0F766E?style=for-the-badge&logo=gmail&logoColor=white" /></a>
<a href="https://wa.me/17018854218"><img alt="WhatsApp +1 (701) 885-4218" src="https://img.shields.io/badge/WhatsApp-%2B1_(701)_885--4218-25D366?style=for-the-badge&logo=whatsapp&logoColor=white" /></a>
<a href="https://t.me/identixia"><img alt="Telegram @identixia" src="https://img.shields.io/badge/Telegram-%40identixia-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" /></a>

</div>

---
