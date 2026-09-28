# RunPod access

Verified on 28 September 2026 using the pod supplied for this project.
Run all local commands below from the repository root.

## Connect

Machine-specific endpoints and host keys are saved in `temporal-evidence-graphs/.local/`,
which is ignored by Git. The configuration references the existing local
`~/.ssh/id_rsa` identity; the provider's example `~/.ssh/id_ed25519` is absent
on this machine. Private keys were neither copied nor added to the repository.

Direct SSH:

```sh
ssh -F temporal-evidence-graphs/.local/ssh_config bdcc-evidence-runpod
```

SFTP was also verified with a read-only working-directory request:

```sh
sftp -F temporal-evidence-graphs/.local/ssh_config bdcc-evidence-runpod
```

Gateway SSH (interactive; no SCP/SFTP):

```sh
ssh -F temporal-evidence-graphs/.local/ssh_config bdcc-evidence-gateway
```

The gateway authenticated using the existing local known-hosts file. The pod's
ED25519 host public key was read through that authenticated session and pinned in
`.local/known_hosts` before the successful direct SSH connection with strict host
checking. Its fingerprint is:

```text
SHA256:58TG3HkO8iMd1zkZ+943NzOEzLGpsXByx5mL5eaMCZM
```

Pod endpoints and host keys can change when a pod is replaced. Refresh the local
configuration against the intended pod if that happens. A fresh checkout on
another machine requires its own local connection configuration and authorized key.

## Jupyter

Jupyter responded with HTTP 302 on pod loopback port 8888. To access it through
the direct SSH connection, keep this command running locally:

```sh
ssh -F temporal-evidence-graphs/.local/ssh_config \
  -N -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:18888:127.0.0.1:8888 bdcc-evidence-runpod
```

Then open <http://127.0.0.1:18888> and use the pod's existing Jupyter credentials
if prompted. Port 18888 is a local choice; remote Jupyter remains on port 8888.
Stop the tunnel with Ctrl+C.

## Observed environment

| Item | Observed value |
|---|---|
| Container hostname | `486f226db1c3` |
| SSH user | `root` |
| GPU | NVIDIA GeForce RTX 5090 |
| GPU memory | 32,607 MiB total; 2 MiB used at initial check |
| GPU compute processes | None reported at direct SSH check |
| NVIDIA driver | 580.126.16 |
| Python | 3.12.3 |
| Installed PyTorch distribution | 2.8.0+cu128 |
| JupyterLab / Notebook | 4.4.9 / 7.4.2 |
| Cgroup memory limit | 93,999,996,928 bytes |
| Cgroup CPU quota | 2,720,000 / 100,000 microseconds (27.2 CPU equivalents) |
| Filesystem | `/` and `/workspace` both reported the overlay filesystem, approximately 75 GiB available |

These are setup observations, not experimental results or a GPU execution test.
Filesystem capacity does not establish persistence or the account's storage quota.
The software stack for the new paper remains to be selected from the research plan.
