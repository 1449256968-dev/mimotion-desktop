# MiMotion Desktop

**English** | [中文](README.md)

MiMotion Desktop is a small Windows GUI for manually submitting a Xiaomi Motion step count. The EXE runs locally and performs the upstream login and submission requests directly; it does not require Python, GitHub Actions, or repository secrets.

> Current release: `v1.0.0` · Windows x64 · Local EXE

[Download the EXE and SHA-256 files](https://github.com/1449256968-dev/mimotion-desktop/releases/tag/v1.0.0)

## Usage

1. Download `MiMotionDesktop.exe` and double-click it. No Python, GitHub account, Actions workflow, or configuration file is required.
2. Enter your Xiaomi Motion account and password, then click **Verify login**. The account must be a Xiaomi Motion account, not a Xiaomi account.
3. Enter the minimum and maximum step counts. Use the same value in both fields for a fixed count.
4. Click **Submit steps** and read the result in the log. After a successful response, check the third-party app that is already linked to Xiaomi Motion.

## This release

- Simple Chinese Windows GUI with verify-login and submit-step actions.
- Runs the request worker in the background so the window stays responsive.
- Uses a direct range or fixed value for the submitted step count.
- Includes cancellation, masked account logs, safe error messages, and a bundled EXE.

## Limitations

- Manual, single-account use; there is no scheduled job or multi-account manager.
- An internet connection is required because the application calls the upstream login and submission endpoints.
- A successful endpoint response does not guarantee that WeChat, Alipay, or another linked service has synchronized the count.
- Upstream endpoint behavior and account binding can change. The author cannot guarantee universal synchronization.

## Source layout

| Path | Purpose |
| --- | --- |
| `desktop_app.py` | Tkinter desktop interface and local settings handling |
| `desktop_core.py` | Login, payload construction, submission, validation, and cancellation |
| `assets/` | Application icon and step payload template |
| `tests/` | Offline mock tests for the core and GUI state machine |
| `build-desktop.ps1` | Windows PyInstaller build script |
| `INSTALL.md` | Chinese installation and usage notes |

The public source repository is a clean desktop edition and intentionally omits the upstream repository's original `main.py`, GitHub Actions workflows, and Git history.

## Privacy

The password is used only for the current operation and is not persisted or written to application logs. If you enable “Remember account and step settings”, the application stores only the account and step range in `%LOCALAPPDATA%\MiMotionDesktop\settings.json`; it never stores the password. Uncheck that option to remove the saved settings.

## Attribution

This desktop edition adapts the Xiaomi Motion login and submission protocol from [mimotion-run](https://github.com/xunichanghuan/mimotion-run) by xunichanghuan and contributors. The upstream project is licensed under the Apache License 2.0. The adapted upstream reference commit is `f038d289cc588e51ce357cb851302e0618f8c167`.

The desktop UI, validation, cancellation, local settings behavior, tests, packaging, and documentation in this repository are modifications for this edition. See `NOTICE.txt` and `LICENSE` for attribution and license terms.

## Verification

The release was checked with 18 offline mock tests and a Windows EXE launch check. A user also reported successful login verification. No claim is made that every account or linked third-party service will synchronize successfully.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).
