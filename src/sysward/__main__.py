"""Entry point for sysward."""

from sysward.app import SyswardApp


def main() -> None:
    app = SyswardApp()
    app.run()


if __name__ == "__main__":
    main()
