# Fonk

Fonk is an open-source command runner that is fully configured via `pyproject.toml`.

## Usage

First add an entry into your `pyproject.toml` file that contains the command you want to run:

```toml
[tool.fonk.command.my_command]
description = "Run my command"
command = "echo Hello"
type = "shell"
``` 

Then run the command using the following command:

```bash
uvx fonk my_command
```
## Contributing

We welcome contributions from the community. To contribute to Fonk, follow these steps:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes.
4. Commit your changes (`git commit -m 'feat: Add new feature'`).
5. Push to the branch (`git push origin feature-branch`).
6. Open a pull request.

Please ensure your code adheres to our coding standards. Since this is a task runner, the required CI steps are also defined as Fonk commands in the `pyproject.toml` file. Simply use `uv run fonk` to run all steps.

## License

Fonk is licensed under the MIT License. See the [LICENSE](./LICENSE.md) file for more details.

## Contact

For any questions or feedback, please open an issue on the [GitHub repository](https://github.com/yourusername/fonk).
