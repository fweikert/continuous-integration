import os
os.environ["BUILDKITE_ORGANIZATION_SLUG"] = "bazel"
os.environ["BUILDKITE_PIPELINE_SLUG"] = "foo"

import aggregate_incompatible_flags_test_result

issue_client = aggregate_incompatible_flags_test_result.GitHubIssueClient("bazel-flag-bot", "")

#i = client.get_issue("fweikert", "bugs", aggregate_incompatible_flags_test_result.get_final_issue_title("Envoy", "3.0", "--incompatible_load_cc_rules_from_bzl"))
#print(i)

links_per_project_and_flag = {("Envoy", "--incompatible_load_cc_rules_from_bzl"): "test link"}
details_per_flag = {"--incompatible_load_cc_rules_from_bzl": aggregate_incompatible_flags_test_result.FlagDetails("3.0", "http://issue")}

for (project_label, flag), links in links_per_project_and_flag.items():
    try:
        details = details_per_flag.get(flag, (None, None))
        if details.bazel_version in (None, "unreleased binary"):
            raise Exception(
                "Notifications: Invalid Bazel version '{}' for flag {}".format(
                    details.bazel_version or "", flag
                )
            )

        if not details.issue_url:
            raise Exception(
                "Notifications: Missing GitHub issue URL for flag {}".format(flag)
            )

        # TODO(fweikert): Remove once the script is stable (#869)
        repo_owner = "fweikert"
        repo_name = "bugs"

        temporary_title = aggregate_incompatible_flags_test_result.get_temporary_issue_title(project_label, flag)
        final_title = aggregate_incompatible_flags_test_result.get_final_issue_title(project_label, details.bazel_version, flag)
        has_target_release = details.bazel_version != "TBD"

        # Three possible scenarios:
        # 1. There is already an issue with the target release in the title -> do nothing
        # 2. There is an issue, but without the target release, and we now know the target release -> update title
        # 3. There is no issue -> create one
        if issue_client.get_issue(repo_owner, repo_name, final_title):
            print(
                "There is already an issue in {}/{} for project {}, flag {} and Bazel {}".format(
                    repo_owner, repo_name, project_label, flag, details.bazel_version
                )
            )
        else:
            number = issue_client.get_issue(repo_owner, repo_name, temporary_title)
            if number:
                if has_target_release:
                    issue_client.update_title(repo_owner, repo_name, number, final_title)
            else:
                body = aggregate_incompatible_flags_test_result.create_issue_body(project_label, flag, details, links)
                title = final_title if has_target_release else temporary_title
                issue_client.create_issue(repo_owner, repo_name, title, body)
    except Exception as ex:
        print("Could not notify project '{}': {}".format(project_label, ex))
