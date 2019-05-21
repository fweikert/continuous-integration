#!/usr/bin/env python3
#
# Copyright 2018 The Bazel Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import bazelci
import itertools
import os
import subprocess
import sys
import time
import yaml


CONFIG_PATH = ".bazelci/federation.yml"
DEFAULT_SCRIPT_URL = "https://raw.githubusercontent.com/bazelbuild/continuous-integration/master/buildkite/federation_ci.py"
BAZEL_VERSION_FILE = ".bazelversion"
REPO_BZL_PATH = "repositories.bzl"


def print_tasks(bazel_version, test_rules_at_head, flip_incompatible_flags, script_url):
    bazelci.print_collapsed_group("Retrieving external dependencies from %s" % REPO_BZL_PATH)
    repositories, archives = parse_repositories_file()

    if test_rules_at_head:
        # TODO(fweikert): remove once implemented
        raise NotImplementedError("--test_rules_at_head isn't supported yet")
        # for each repo/archive:
        #   fetch latest release
        #   store version
        # rewrite repo file
        # execute_command(["buildkite-agent", "artifact", "upload", REPO_BZL_PATH])

    if flip_incompatible_flags:
        # TODO(fweikert): remove once implemented
        raise NotImplementedError("--flip_incompatible_flags isn't supported yet")

    bazelci.print_collapsed_group("Printing pipeline steps")
    external_root = download_external_repositories()
    pipeline_steps = []
    for kwargs in itertools.chain(repositories, archives):
        project = kwargs.get("name")
        if not project:
            raise bazelci.BuildkiteException(
                "Malformed %s file: Missing key 'name'" % (REPO_BZL_PATH)
            )

        config_path = os.path.join(external_root, project, CONFIG_PATH)
        if not os.path.exists:
            raise bazelci.BuildkiteException(
                "No configuration for project %s at %s" % (project, config_path)
            )

        all_tasks = load_tasks_from_config(project, config_path)
        for task, task_config in all_tasks.items():
            run_step = create_task_step(
                project=project,
                task=task,
                platform=get_platform_for_task(task_config, task),
                bazel_version=bazel_version,
                test_rules_at_head=test_rules_at_head,
                flip_incompatible_flags=flip_incompatible_flags,
                script_url=script_url,
            )
            pipeline_steps.append(run_step)

    bazelci.print_pipeline_steps(pipeline_steps)


def parse_repositories_file():
    def fake_load(*args):
        pass

    repositories = []
    archives = []

    def fake_git_repository(**kwargs):
        repositories.append(kwargs)

    def fake_http_archive(**kwargs):
        archives.append(kwargs)

    class FakeNativeModule(object):
        def existing_rules(self):
            return ()

    try:
        with open(REPO_BZL_PATH, "r") as f:
            content = f.read()
    except IOError as ex:
        raise bazelci.BuildkiteException(
            "Could not read repository file at %s: %s" % (REPO_BZL_PATH, ex)
        )

    exec(
        "%s\nrepositories()" % content,
        {
            "__builtins__": None,
            "load": fake_load,
            "git_repository": fake_git_repository,
            "http_archive": fake_http_archive,
            "native": FakeNativeModule(),
        },
    )

    return repositories, archives


def download_external_repositories(project_filter=None):
    if project_filter:
        bazelci.print_collapsed_group("Downloading external repository '%s'" % project_filter)
        # Use "blaze query" to fetch the external repository, including the configuration file.
        # Query will fail with exit code 2 if the file wasn't exported (which is very likely), but we can
        # ignore this error since the repository will have been downloaded anyway.
        execute_command(
            ["bazel", "query", "@%s//:%s" % (project_filter, CONFIG_PATH)], ignored_exit_codes=[2]
        )
    else:
        bazelci.print_collapsed_group("Downloading all external repositories")
        execute_command(
            ["bazel", "sync"], "Failed to download external repositories via 'bazel sync'"
        )

    bazelci.print_collapsed_group("Locating download directory")
    try:
        output_base = bazelci.execute_command_and_get_output(
            ["bazel", "info", "output_base"], capture_stderr=False
        )
    except subprocess.CalledProcessError as ex:
        raise bazelci.BuildkiteException("Failed to determine the output base directory: %s" % ex)

    return os.path.join(output_base, "external")


def execute_command(args, error_message, ignored_exit_codes=()):
    try:
        bazelci.execute_command(args)
    except subprocess.CalledProcessError as ex:
        if ex.returncode not in ignored_exit_codes:
            raise bazelci.BuildkiteException("%s: %s" % (error_message, ex))


def load_tasks_from_config(project, path):
    try:
        with open(path, "r") as fd:
            config = yaml.safe_load(fd)
    except IOError as ex:
        raise bazelci.BuildkiteException(
            "Could not read configuration file for project %s at %s: %s" % (project, path, ex)
        )

    if "bazel" in config:
        raise bazelci.BuildkiteException(
            "Configuration file %s for project %s specifies an explicit Bazel version for all tasks"
            % (path, project)
        )

    tasks = config.get("tasks") or config.get("platforms")
    if not tasks:
        raise bazelci.BuildkiteException(
            "Configuration %s for project %s does not contain any tasks" % (path, project)
        )

    invalid_tasks = [t for t, tc in tasks.items() if "bazel" in tc]
    if invalid_tasks:
        raise bazelci.BuildkiteException(
            "Configuration file %s for project %s specifies an explicit Bazel version "
            "for the following task(s): %s" % (path, project, ", ".join(invalid_tasks))
        )

    return tasks


def create_task_step(
    project, task, platform, bazel_version, test_rules_at_head, flip_incompatible_flags, script_url
):
    command = "%s federation_ci.py" % bazelci.PLATFORMS[platform]["python"]
    if bazel_version:
        command += " --bazel_version=%s" % bazel_version
    if test_rules_at_head:
        command += " --test_rules_at_head=%s" % test_rules_at_head
    if flip_incompatible_flags:
        command += " --flip_incompatible_flags=%" % flip_incompatible_flags

    command = "%s run --project=%s --task=%s" % (command, project, task)

    label = bazelci.create_label(platform, project, task_name=task)
    return bazelci.create_step(
        label=label, commands=[fetch_script_command(script_url), command], platform=platform
    )


def fetch_script_command(raw_url):
    return "curl -sS % -o bazelci.py" % get_script_url(raw_url)


def get_script_url(raw_url):
    return "{}?{}".format(raw_url or DEFAULT_SCRIPT_URL, int(time.time()))


def get_platform_for_task(task_config, task_name):
    return task_config.get("platform", task_name)


def run_task(project_name, task_name, bazel_version, test_rules_at_head, flip_incompatible_flags):
    if bazel_version:
        overwrite_bazel_version(bazel_version)
    if test_rules_at_head:
        overwrite_repositories_file()

    external_root = download_external_repositories(project_name)
    config_path = os.path.join(external_root, project_name, CONFIG_PATH)
    all_tasks = load_tasks_from_config(config_path)
    task_config = all_tasks.get(task_name)
    if not task_config:
        raise bazelci.BuildkiteException(
            "There is no task '%s' in configuration %s of project %s"
            % (task_name, config_path, project_name)
        )

    rewrite_local_targets(task_config, project_name)
    bazelci.execute_commands(
        task_config=task_config,
        platform=get_platform_for_task(task_config, task_name),
        git_repository=None,
        git_commit=None,
        git_repo_location=None,
        use_bazel_at_commit=False,
        use_but=False,
        save_but=False,
        needs_clean=False,
        build_only=False,
        test_only=False,
        monitor_flaky_tests=False,
        incompatible_flags=None,
        bazel_version=None,
    )


def overwrite_bazel_version(bazel_version):
    bazelci.print_collapsed_group("Setting Bazel version to %s" % bazel_version)
    try:
        with open(BAZEL_VERSION_FILE, "w") as fd:
            fd.write(bazel_version)
    except IOError as ex:
        raise bazelci.BuildkiteException(
            "Could not overwrite Bazel version file at %s: %s" % (BAZEL_VERSION_FILE, ex)
        )


def overwrite_repositories_file():
    bazelci.print_collapsed_group("Downloading %s with rules at HEAD" % REPO_BZL_PATH)
    execute_command(["buildkite-agent", "artifact", "download", REPO_BZL_PATH, "."])


def rewrite_local_targets(task_config, project_name):
    for key in ("run_targets", "build_targets", "test_targets"):
        for i, target in enumerate(task_config.get(key, ())):
            task_config[key][i] = add_remote_target_prefix(target, project_name)


def add_remote_target_prefix(target, project_name):
    if target == "--":
        return target

    minus = ""
    if target.startswith("-"):
        minus = "-"
        target = target[1:]

    slashes = "" if target.startswith("//") else "//"
    return "%s@%s%s%s" % (minus, project_name, slashes, target)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    yaml.add_representer(str, bazelci.str_presenter)

    parser = argparse.ArgumentParser(description="Bazel Federation Continuous Integration Script")
    parser.add_argument("--bazel_version", type=str)
    parser.add_argument("--test_rules_at_head", type=bool)
    parser.add_argument("--flip_incompatible_flags", type=bool)

    subparsers = parser.add_subparsers(dest="subparsers_name")

    print_parser = subparsers.add_parser("print")
    print_parser.add_argument("--script_url", type=str)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--project", type=str)
    run_parser.add_argument("--task", type=str)

    args = parser.parse_args(argv)

    try:
        common_kwargs = {
            "bazel_version": args.bazel_version,
            "test_rules_at_head": args.test_rules_at_head,
            "flip_incompatible_flags": args.flip_incompatible_flags,
        }
        if args.subparsers_name == "print":
            print_tasks(script_url=args.script_url, **common_kwargs)
        elif args.subparsers_name == "run":
            run_task(project=args.project, task=args.task, **common_kwargs)
        else:
            parser.print_help()
            return 2
    except bazelci.BuildkiteException as e:
        bazelci.eprint(str(e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
