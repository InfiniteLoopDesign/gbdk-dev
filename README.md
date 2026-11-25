# GBDK starter

Build **Green Light**, a Game Boy Color race-start reaction test. Press A to start the sequence. Five red lights come on one by one, then all go out together after a variable pause. Press A as soon as they go out to see your reaction time in milliseconds. An early press is a jump start. Press A again to retry.

## Start a blank project

On the Linux host where you use VS Code remotely, open this checkout. Both launchers require Docker with the Compose plugin.

- **Build the toolchain from the GitHub checkout.** Run `./new-project.sh`. Docker builds the development image locally using the Debian base from Amazon ECR Public and the pinned GBDK release archive. This path needs Docker and internet access for the base image and packages. [Docker Official Images on Amazon ECR Public](https://aws.amazon.com/blogs/containers/docker-official-images-now-available-on-amazon-elastic-container-registry-public/)
- **Use the published toolchain.** Run `./new-project-from-image.sh`. Docker uses the published `daviau/gbdk-dev:4.6.0` image at its release digest and adds a small layer to match the host user. [Docker Hub image](https://hub.docker.com/r/daviau/gbdk-dev)

Enter a project name of up to 18 characters and a new directory path. The default is a folder next to this repository. The launcher initializes Git, starts the dev container, builds `build/game.gbc`, and checks the cartridge header and display title. It prints the absolute dev directory and ROM paths. Open the dev directory in remote VS Code and choose **Dev Containers: Reopen in Container**. Open the ROM in an emulator to see your project name and three looping gold sparkles.

For a scripted launch, pass both values directly to either launcher.

```sh
./new-project.sh "Orbit Test" "$HOME/dev/orbit-test"
```

Run `docker compose down` from the generated directory when done with the container. The project's README explains how to rebuild and retrieve the ROM.

## Build your first ROM

Install Docker and start it. Open a terminal in this folder, where you can see the `Dockerfile` and `Makefile`.

```sh
docker build -t gbdk-dev:4.6.0 .
docker run --rm --mount "type=bind,source=$PWD,target=/workspace" gbdk-dev:4.6.0 make
```

The first command builds the toolchain image. Run the second command each time you change the game. Docker mounts this folder into the container, so `build/green-light.gbc` appears in your checkout and stays there when the container exits.

These commands use a Bash-compatible shell. On Linux, if the build folder is unwritable because your host user has a different numeric ID, add `--user "$(id -u):$(id -g)"` after `--rm`. On Windows, run the commands from WSL with Docker integration enabled, or use the VS Code workflow below.

## Run it and make a change

1. Open `build/green-light.gbc` in a Game Boy Color emulator such as [SameBoy](https://sameboy.github.io/). Look in your emulator's input settings for the key mapped to Game Boy A.
2. In `src/main.c`, change `GREEN LIGHT` to a short title of your own. Save the file and build again.
3. Reload or reopen the ROM in the emulator and check the title. Keep the editor and emulator open while you iterate.

`make` skips the build when the source and Makefile are unchanged. Run `make clean` inside the container to remove generated files and start fresh.

Use `git status` to see your source changes. If you're starting with an empty Git history, run `git add .` and `git commit -m "Start GBDK project"` to save the starter. For later game edits, stage just the changed file with `git add src/main.c` and commit with a short message. Git ignores the generated `build/` folder.

## Work in VS Code, locally or remotely

1. Install VS Code and its **Dev Containers** extension. Open this folder and run **Dev Containers: Reopen in Container** from the command palette.
2. In the container terminal, run `make`, or choose **Terminal → Run Build Task**. The build task runs the same Makefile.

For a remote setup, keep the Git checkout on a Linux host that has Docker. Connect to the host with VS Code **Remote - SSH**, or start `code tunnel` on that host and connect through **Remote - Tunnels**. Open the checkout on the host, then choose **Reopen in Container**. The host checkout holds your source, Git history, and ROM builds even when the container is rebuilt. [Remote SSH setup](https://code.visualstudio.com/docs/remote/ssh#_open-a-folder-on-a-remote-ssh-host-in-a-container) · [Remote Tunnels setup](https://code.visualstudio.com/docs/remote/tunnels/)

Use HTTPS Git remotes inside the container. For a Git remote that uses SSH, run Git commands in the host checkout where your SSH client and keys are available.

## Deploy your ROM for playtesting

The `.gbc` file is the entire playable build. On a remote SSH host, copy it to your computer. Run this from your computer and replace the login and path with your own.

```sh
scp dev@your-host:/path/to/checkout/build/green-light.gbc .
```

You can also download the file from VS Code's remote Explorer. To play on a phone, transfer the ROM to the phone and open it in a GBC emulator, or import it from the phone's files into the [SkyEmu browser player](https://web.skyemu.app/). To share a build, attach the ROM to a release in your Git hosting service. Give each release a version so testers know which build they are playing.

## Where things live

| Path | What to change there |
| --- | --- |
| `src/main.c` | Game logic, controls, and colors |
| `Makefile` | How the game compiles and where the ROM goes |
| `Dockerfile` | Debian base and the pinned GBDK toolchain |
| `.devcontainer/` and `.vscode/` | How VS Code opens the container and runs the build |
| `build/` | Generated ROM and other build output. Git ignores this folder. |

The image installs the official [GBDK-2020 4.6.0 release](https://github.com/gbdk-2020/gbdk-2020/releases/tag/4.6.0) for Linux amd64 or arm64, plus Make and Git. Downloads are checked against the release SHA-256 digests. The container runs as the `dev` user.
