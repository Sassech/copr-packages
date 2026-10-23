# COPR "make_srpm" entry point. COPR runs:
#   make -f <clone>/.copr/Makefile srpm outdir=<dir> spec=<spec path>
# Local usage (from the repo root):
#   make -f .copr/Makefile srpm spec=rmpc/rmpc.spec
TOPDIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
outdir ?= $(TOPDIR)/_build/srpm
spec ?=

.PHONY: srpm
srpm:
	bash "$(TOPDIR)/scripts/make-srpm.sh" "$(spec)" "$(outdir)"
