"""PyInstaller entry; packaged source remains available for manual handoffs."""
import sys
sys.dont_write_bytecode = True
from project_harness.windows_package import frozen_main
raise SystemExit(frozen_main())
