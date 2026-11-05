# Usage

## Create and organize a lab

From **Labs**, create a lab with a title and platform. A category, source URL, difficulty, and status are optional. Platforms and categories can be created from the form. The list supports search, platform/category/status filters, and pagination.

Status values are To do, In progress, Solved, and Documented. Marking a lab Solved records its solved timestamp; changing it away from Solved clears that timestamp.

## Record work

Use **Notes** for commands, requests, code, and observations. Notes are plain text that may contain Markdown. Select **Save notes** before navigating away; unsaved changes are marked and trigger a browser-close warning.

Use **Findings** for distinct vulnerabilities. Findings can be ordered and include category, CWE, status, description, technical details, reproduction steps, impact, and mitigation. CVSS version, vector, score, severity, and justification are optional manual inputs; TraceLab does not calculate a score.

## Manage evidence

The **Evidence** tab accepts PNG, JPEG, WebP, UTF-8 TXT, and HTTP files. Defaults allow 10 MB per file, 10 files per upload, and 100 files per lab. The backend verifies signatures or text encoding rather than trusting the browser content type.

Evidence can be previewed, downloaded, captioned, assigned a step, associated with a finding, reordered, or deleted. Duplicate content in the same lab is rejected. Review all content before sharing it.

## Generate and edit a report

Open **Report**, complete objective and learnings when applicable, and select **Generate Markdown**. Findings and evidence are included in saved order. Missing optional content is omitted.

Code view is an editable Markdown textarea. Preview safely displays supported headings, paragraphs, bullets, fenced code, and exported evidence images. Save changes explicitly. Regeneration asks for confirmation because it replaces manual edits.

## Export

1. Save pending Markdown changes.
2. Review report warnings and every selected evidence file.
3. Keep selected any evidence referenced from Markdown.
4. Confirm the sensitive-information review checkbox.
5. Select **Export ZIP**.

The backend rejects active HTML, external Markdown images, unsafe paths, cross-lab evidence, missing referenced evidence, and oversized exports. The browser downloads `<lab-slug>.zip`; TraceLab does not publish it to GitHub.

## Demonstration

[`examples/demo-lab`](../examples/demo-lab/README.md) is a static generated-output example. Its target, request, and response are fictional. To reproduce it, create **Demo Authorization Review**, copy its report data, and upload its two synthetic evidence files.
