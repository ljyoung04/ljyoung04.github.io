---
# the default layout is 'page'
icon: fas fa-info-circle
order: 4
---

<style>
  #cve-list + table {
    table-layout: fixed;
    width: 100%;
  }

  #cve-list + table th,
  #cve-list + table td {
    overflow-wrap: anywhere;
    word-break: keep-all;
  }

  a.shimmer:has(> img.about-profile-photo) {
    background: transparent;
  }

  a.shimmer:has(> img.about-profile-photo)::before {
    content: none;
    animation: none;
  }
</style>

<div style="display: flex; gap: 2rem; align-items: center; flex-wrap: wrap; margin-bottom: 2rem;">
  <div style="flex: 0 0 180px;">
    <img
      class="about-profile-photo"
      src="/assets/img/face.jpg"
      alt="Profile photo"
      style="width: 180px; height: 180px; object-fit: cover; border-radius: 50%;"
    >
  </div>

  <div style="flex: 1 1 280px;">
    <h2 style="margin-top: 0;">이준영</h2>
    <p>
      울산대학교 IT융합학부 재학 (2023 ~ ) <br>
      울산대학교 IT융합학부 정보보안 동아리 UNKNOWN (2023 ~ ) <br>
      차세대 보안리더 양성 프로그램 Whitehat School 3기 수료 (2025) <br>
    </p>
  </div>
</div>

## Skills

- Programming
    - C, Python
- Vulnerability Research
    - Pwnable, Web, Linux Kernel


## CVE List
{: #cve-list }

| CVE | Description | Link |
| --- | --- | --- |
| CVE-2025-6218 | RARLAB WinRAR Directory Traversal Remote Code Execution Vulnerability | [ZDI-25-409](https://www.zerodayinitiative.com/advisories/ZDI-25-409/) |

## Awards

| Award | Organization | Date |
| --- | --- | --- |
| 화이트햇 스쿨 우수 프로젝트 | 한국정보기술연구원 | 2025.09.24 |
| 2026 동남권 정보보호 사이버 공방전 대상 | 과학기술정보통신부 | 2026.07.14 |

## Certifications

| Certification | Issuer | Date |
| --- | --- | --- |
|  |  |  |
