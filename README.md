## [WIP] Norsu -- PostgreSQL builds manager

### Introduction

Norsu (finnish for *elephant*) is meant to be a tool for quickly installing
and updating custom PostgreSQL builds, as well as testing your extensions
against them.

This might be useful if you're an extension developer and you aim to support
several major PostgreSQL releases. Over time, running regression test suites
against a growing number of releases might become a combersome task, hence a
need for an automation tool.

Currently, Norsu can:

* install & remove PostgreSQL release- and dev- branches and keep them up-to-date;
* show various properties of builds (configure flags, commit hash, version etc);
* search for branches across multiple git repos (specified in a config file);
* install and test PostgreSQL extensions using regression test suites;

### Setup

> NOTE: Python 3.3+ is required.

To install a stable release, just run the following in your favorite shell:

```bash
pip install --user norsu
```

and you're good to go!


To install a dev version, clone this repo and run:

```
pip install --user -U .
```

The config file is located at `$NORSU_PATH/.norsu.toml` (by default, `$NORSU_PATH` is `$HOME/pg`).

### Usage

> NOTE: the public API **has not been stabilized yet**, it's better to take a look at this page from time to time.

In general,

* If a command accepts `[target]...`, it will default to all available builds if no target is specified;
* Targets may be versions (e.g. `10`, `9.6.8`, `9.5`) or (parts of) branch names (e.g. `master`, `REL_10`);
* Target might be positive (e.g. `master`, `9.6.5`, `10`) and negative (i.e. exclude some build, e.g. `^master`);
* An interrupted command will try to continue where it left off next time;
* Time-consuming commands print steps they're taking to achieve goals;

Here's a non-exhaustive list of provided commands:

#### `norsu install [target]...`

For each `target`:

* if **not yet installed**, find a list of **matching** branches in known git repos (specified in config file),
select the most relevant one, configure and install it to `$NORSU_PATH/target`.

* if **already installed**, check the branch for updates (new commits), then rebuild and/or reinstall if necessary.

Example:

```bash
# install some releases
$ norsu install 9.5 9.6 10
Selected instance: 9.5
        => No work dir, choosing repo & branch
        => Selected repo git://git.postgresql.org/git/postgresql.git
        => Selected branch REL9_5_STABLE
        ...
```

#### `norsu search [target]...`

For each `target`, print a list of matching branches to be used by `install` command.
Currently, a branch matches if `target` occurs in its name (is a substring).

Branches are sorted by decreasing priority:
* if `target` is version, branches are sorted by "freshness" (the most fresh release wins);
* otherwise, branches are sorted by similarty (the most similar name wins);

Example:

```bash
$ norsu search 10
Search query: 10
         REL_10_STABLE
         REL_10_4
         REL_10_3
         REL_10_2
         REL_10_1
         REL_10_0
         REL_10_RC1
         ...
```

#### `norsu pull [target]...`

For each `target`, pull new commits from a git repo (but don't re-build anything).
This command prints the amount of new commits available and updates info shown by `status` command.

#### `norsu status [target]...`

Print some info about each `target`, for instance:

```
Selected instance: master
Status:        Installed (out of date)
Main dir:      $HOME/pg/master
Work dir:      $HOME/pg/.norsu/master
Branch:        master
Version:       PostgreSQL 11beta1
Commit:        6a75b58065c8da69a259657fc40d18e76157f265
CONFIGURE:     ['CFLAGS=-g3', '--enable-cassert']
```

#### `norsu remove [target]...`

Remove `targets` (main dirs) and their cached git repos (work dirs).

#### `norsu pgxs [target]... [cmd_option]... [-- [make_option]...]`

Where:

* `target` -- run make targets argainst the specified builds
* `cmd_option` -- additional options for this command, e.g. `--run-pg`
* `make_option` -- options to be passed to `make`, e.g. `clean install -j5`

Known `cmd_options`:

* `-R`, `--run-pg` -- start a temp instance of PostgreSQL for the duration of command

> NOTE: this command should be executed in extension's directory

For each `target`, executes `make USE_PGXS=1 PG_CONFIG=path/to/pg_config ...` in extension's directory.

Examples:

```bash
# install to all builds
norsu pgxs

# install to everything but master (rules and options are passed to make)
norsu pgxs ^master -- clean install -j5

# run regression tests against 9.6.9
norsu pgxs 9.6.9 -R -- installcheck

# check using clang-analyzer for builds 9.6 and 10
scan-build norsu pgxs 9.5 10 -- clean all
```

#### `norsu path [target]...`

Print paths to install dirs of `targets`.

#### `norsu purge [target]...`

For each `target`, remove orphaned git repos (work dirs).


### Miscellaneous

Don't hesitate to open new issues and express your ideas!
