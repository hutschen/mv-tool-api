# MV-Tool

MV-Tool is for tracking measures in information security. If information security is to be implemented according to [BSI IT Grundschutz](https://www.bsi.bund.de/DE/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/IT-Grundschutz/IT-Grundschutz-Kompendium/it-grundschutz-kompendium_node.html) or another procedure or standard, many information security measures need to be implemented.

MV-Tool supports this process insofar as concrete implementation steps (measures) can be determined for each information security requirement. The implementation of these measures can later be tracked in an issue tracker. Currently, only JIRA by [Atlassian](https://www.atlassian.com/software/jira) is supported as issue tracker.

## Installation

MV tool consists of two components, the web API and the [web client](https://github.com/hutschen/mv-tool-ng). This repository contains the web API. For installation in a production environment, deployment using Docker is recommended. You can find the appropriate Docker container on [Docker Hub](https://hub.docker.com/r/hutschen/mv-tool) or you can build by using the Dockerfile, which you can find in [a separate repository](https://github.com/hutschen/mv-tool-docker).

## Contributing

The goal of MV-Tool is to provide its users with the greatest possible benefit in their daily work in information security. For this reason, feedback from the field and suggestions for improvement are particularly important.

If you want to contribute something like this, feel free to create an issue with a feature request, an idea for improvement or a bug report. Issues can be created in English and German.

This project is just started. Later there will be more possibilities to contribute. For now please be patient. Thanks :relaxed:

## License and dependencies

The MV tool itself or the source code in this repository is licensed under AGPLv3. You find the license in the [license file](LICENSE). In addition, MV-Tool uses a number of libraries to make it work. These libraries have been released by their respective authors under their own licenses. These libraries or their source code is not part of this repository.
