# Install once; supply a new title for each paper

Platform guidance checked against official documentation on 11 October 2026. Availability depends on account/workspace/tools; recheck when the interface changes.

## Codex

The local installation supplied with this package is discoverable under the user's skills folder. Invoke `$review-paper-studio` and provide the title, optional field, and any overrides. Current official documentation also describes user skills under ~/.agents/skills; avoid installing duplicate skills with the same name in multiple discovered roots. If an installed change does not appear, refresh/restart the session rather than claiming it is already loaded.

Example: `$review-paper-studio Title: Explainable AI for Early Detection of Alzheimer's Disease. Field: medical AI. Use my defaults and deliver the illustrated PDF with separate support.`

Official source: https://learn.chatgpt.com/docs/build-skills

## Claude

Use review-paper-studio.zip, which contains one top-level review-paper-studio folder and its SKILL.md plus resources. In Claude, go to Customize > Skills, choose the add/create option and Upload a skill, upload the ZIP and enable it. Enable the available code execution/file-creation capability; research still needs actual browsing or supplied sources. Do not assume the skill grants access to subscription databases.

Start a new conversation: `Use Review Paper Studio. Title: [your title]. Field: [optional field]. Use the saved defaults.`

Official sources: https://support.claude.com/en/articles/12512198-how-to-create-custom-skills and https://support.claude.com/en/articles/12512180-use-skills-in-claude

## ChatGPT

Where plugin creation is enabled, use Plugin Creator to create a private Review Paper Studio workflow from the supplied instruction file and reference resources. Test web research, file creation and rendering in the actual Chat or Work surface; a plugin or uploaded file does not itself grant capabilities. Follow the visible creation/install steps rather than assuming a local ZIP has already become an installed ChatGPT plugin. A standalone skill ZIP is not a complete universal plugin manifest.

If that interface is unavailable, keep CHATGPT_INSTRUCTIONS.md and the reference resources in a dedicated ChatGPT project where supported. Instruct ChatGPT to follow that file for each new title. This is an instruction-based fallback, not a claim of native skill installation. Do not put the entire long research workflow into global personalization settings, where it could affect unrelated chats. File creation, browsing and code availability must be checked in the selected surface.

Official sources: https://learn.chatgpt.com/docs/build-plugins and https://learn.chatgpt.com/docs/prompting

One-time setup request: `Create a private Review Paper Studio workflow using the attached instructions and resources. Preserve the default word budget, verified-source requirements, PDF checks and separate supporting files. Do not publish or share it. Tell me which research/file tools are actually available.`

New-paper request: `Use Review Paper Studio. Title: [title]. Field: [field if needed]. Deliver the main PDF and editable Word file, with supporting material separate.`

## Change only what differs

Optional overrides: word target/ceiling; reference preference; field; review type; intended population/application; date window; journal; fee ceiling; citation style; author's supplied identities/declarations; output language. These belong in the project, not every future paper.

`Continue and complete the paper from STATUS.md` resumes saved work. `Change this project's main text to 5000 words` changes one paper. A new title should start a separate workspace. This workflow operates during actual sessions; no automatic background research or submission is installed.

## Honest limits

The package is instruction- and script-backed. It is not a trained model, subscription database, automatic human reviewer or guarantee. Validation checks must not be described as full field-level publication validation. Before submission, accountable human authors verify science, sources/figures, authorship/declarations and current journal eligibility. Acceptance and revision-free publication cannot be guaranteed.
