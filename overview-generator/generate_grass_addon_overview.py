#!/usr/bin/env python3
#
############################################################################
#
# MODULE:      generate_grass_addon_overview.py
# AUTHOR(S):   Anika Weinmann
#
# PURPOSE:     Script to generate a overview of the mundialis GRASS GIS addons
# COPYRIGHT:   (C) 2024 by mundialis GmbH & Co. KG
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
############################################################################

# Call script:
#  python3 generate_grass_addon_overview.py

import json
import subprocess

from datetime import datetime
from jinja2 import Template
import requests

GITHUB_OWNER = "mundialis"
GITHUB_TOPIC = "grass-gis-addons"


def get_grass_family(grass_repos_dict, addon_name):
    """Get GRASS GIS family name"""
    if "." in addon_name:
        grass_family_short = addon_name.split(".")[0]
    else:
        grass_family_short = addon_name.split("_")[0]
    if grass_family_short not in grass_repos_dict:
        grass_repos_dict[grass_family_short] = {}
    return grass_family_short


def get_repo_url_desc(repo):
    """Get repository homepage url and description"""
    gh_url_cmd = [
        "gh",
        "repo",
        "view",
        repo,
        "--json",
        "homepageUrl,description",
    ]
    result = subprocess.run(gh_url_cmd, stdout=subprocess.PIPE)
    result_dict = json.loads(result.stdout.decode().strip())
    return result_dict


def get_repo_content(repo):
    """Get a list of files in the repo"""
    gh_list_repo_content_cmd = [
        "gh",
        "api",
        f"/repos/{repo}/git/trees/main?recursive=true",
        "-q",
        ".tree[]|.path",
    ]
    result = subprocess.run(gh_list_repo_content_cmd, stdout=subprocess.PIPE)
    repo_content_list = result.stdout.decode().strip().split("\n")
    return repo_content_list


def check_test_status(repo):
    """Check the status of the last runned tested"""
    gh_check_actions = [
        "gh",
        "run",
        "list",
        "--repo",
        repo,
        "--workflow",
        "Run tests for GRASS GIS addons",
    ]
    result = subprocess.run(gh_check_actions, stdout=subprocess.PIPE)
    tests_main = [
        x.split("\t")
        for x in result.stdout.decode().split("\n")
        if "main" in x
    ]
    if len(tests_main) > 1:
        testsuite = tests_main[0][1]
    return testsuite


# list mundialis grass-gis-addons repos
gh_list_repo_cmd = [
    "gh",
    "repo",
    "list",
    GITHUB_OWNER,
    "--limit",
    "100",
    "--public",
    "--topic",
    GITHUB_TOPIC,
]
result = subprocess.run(gh_list_repo_cmd, stdout=subprocess.PIPE)
repos = [
    x.split("\t")[0] for x in result.stdout.decode().split("\n") if x != ""
]
# other repos with more addons e.g. mundialis/openeo-addons, mundialis/vale, ...
grass_repos = [x for x in repos if "." in x or x == "mundialis/d_rast_multi"]
no_addon_repos = ["mundialis/grass-gis-helpers"]
other_repos = [
    x
    for x in repos
    if "." not in x
    and x not in no_addon_repos
    and x != "mundialis/d_rast_multi"
]

# loop over grass addon repos
grass_repos_dict = {}
for grass_repo in grass_repos:
    grass_addon_name = grass_repo.split("/")[1]

    # get github pages url
    result_dict = get_repo_url_desc(grass_repo)
    if not result_dict["homepageUrl"]:
        homepage_url = (
            f"https://github.com/{grass_repo}/tree/main/{grass_addon_name}"
        )
    else:
        homepage_url = result_dict["homepageUrl"]

    # get grass family
    grass_family_short = get_grass_family(grass_repos_dict, grass_addon_name)

    # get addon description
    desc = result_dict["description"]

    # check if testsuite exists
    repo_content_list = get_repo_content(grass_repo)
    testsuite = "no"
    if "testsuite" in repo_content_list:
        testsuite = "yes"
    testsuite = check_test_status(grass_repo)

    # add repo to dict
    grass_repos_dict[grass_family_short][grass_addon_name] = {
        "url": homepage_url,
        "description": desc,
        "testsuite": testsuite,
    }

# loop over other repos
for repo in other_repos:
    repo_content_list = get_repo_content(repo)
    addons_dir = ""
    for addons_dir_base in ["grass-gis-addons", "grass_addons"]:
        if addons_dir_base in repo_content_list:
            addons_dir = f"{addons_dir_base}/"
            break
    html_files = [
        x.replace(addons_dir, "")
        for x in repo_content_list
        if x.endswith(".html")
    ]
    testsuite = "no"
    if f"{addons_dir_base}/testsuite" in repo_content_list:
        testsuite = "yes"
        testsuite = check_test_status(grass_repo)
    for html_file in html_files:
        splitted_name = html_file.split("/")
        if f"{splitted_name[0]}.html" == splitted_name[-1]:
            addon_name = splitted_name[0]
            # get grass family
            grass_family_short = get_grass_family(grass_repos_dict, addon_name)
            # get addon description
            result_dict = get_repo_url_desc(repo)
            desc_additional = result_dict["description"]
            url = (
                f"https://raw.githubusercontent.com/{repo}/main/"
                f"{addons_dir}{html_file.replace('html', 'py')}"
            )
            resp = requests.get(url)
            if resp.status_code == 404:
                url = (
                    f"https://raw.githubusercontent.com/{repo}/main/"
                    f"{addons_dir}{html_file}"
                )
                resp = requests.get(url)
                addon_desc = (
                    [
                        x
                        for x in resp.content.decode().split("\n")
                        if (x.startswith(f"<em><b>{addon_name}</b></em>"))
                    ][0]
                    .replace("# % description:", "")
                    .replace("#% description:", "")
                )
            else:
                addon_desc = (
                    [
                        x
                        for x in resp.content.decode().split("\n")
                        if (
                            x.startswith("# % description:")
                            or x.startswith("#% description:")
                            or x.startswith("#%description:")
                        )
                    ][0]
                    .replace("# % description:", "")
                    .replace("#% description:", "")
                    .replace("#%description:", "")
                )
            desc = f"{desc_additional} - {addon_desc}".replace("  ", " ")
            # check if testsuite exists TODO
            if testsuite == "yes":
                addon_dir = html_file.rsplit("/", 1)[0]
                testsuite_dir = f"{addon_dir}/testsuite"
                if f"{addon_dir}/testsuite" in repo_content_list:
                    testsuite = "yes"
            # get homepage_url
            if not result_dict["homepageUrl"]:
                homepage_url = (
                    f"https://github.com/{repo}/tree/main/"
                    f"{addons_dir}{addon_name}"
                )
            else:
                homepage_url = result_dict["homepageUrl"]
            # add repo to dict
            grass_repos_dict[grass_family_short][addon_name] = {
                "url": homepage_url,
                "description": desc,
                "testsuite": testsuite,
            }

# set other variables
now = datetime.utcnow()
date = now.strftime("%d %b %Y")
date_utc = now.strftime("%a %b %d %H:%M:%S UTC %Y")
current_year = now.strftime("%Y")

# template
with open("template_index.html") as f:
    tmpl = Template(f.read())

tmpl_param = {
    "date": date,
    "date_utc": date_utc,
    "number_addons": 0,
    "current_year": current_year,
}
if "d" in grass_repos_dict:
    tmpl_param["number_addons"] += len(grass_repos_dict["d"])
    tmpl_param["display_addons"] = grass_repos_dict["d"]
if "db" in grass_repos_dict:
    tmpl_param["number_addons"] += len(grass_repos_dict["db"])
    tmpl_param["db_addons"] = grass_repos_dict["db"]
if "g" in grass_repos_dict:
    tmpl_param["number_addons"] += len(grass_repos_dict["g"])
    tmpl_param["general_addons"] = grass_repos_dict["g"]
if "i" in grass_repos_dict:
    tmpl_param["number_addons"] += len(grass_repos_dict["i"])
    tmpl_param["imagery_addons"] = grass_repos_dict["i"]
if "m" in grass_repos_dict:
    tmpl_param["number_addons"] += len(grass_repos_dict["m"])
    tmpl_param["misc_addons"] = grass_repos_dict["m"]
if "ps" in grass_repos_dict:
    tmpl_param["number_addons"] += len(grass_repos_dict["ps"])
    tmpl_param["postscript_addons"] = grass_repos_dict["ps"]
if "r" in grass_repos_dict:
    tmpl_param["number_addons"] += len(grass_repos_dict["r"])
    tmpl_param["raster_addons"] = grass_repos_dict["r"]
if "r3" in grass_repos_dict:
    tmpl_param["number_addons"] += len(grass_repos_dict["r3"])
    tmpl_param["drast_addons"] = grass_repos_dict["r3"]
if "t" in grass_repos_dict:
    tmpl_param["number_addons"] += len(grass_repos_dict["t"])
    tmpl_param["temporal_addons"] = grass_repos_dict["t"]
if "v" in grass_repos_dict:
    tmpl_param["number_addons"] += len(grass_repos_dict["v"])
    tmpl_param["vector_addons"] = grass_repos_dict["v"]

with open("grass_addon_overview.html", "w") as f:
    f.write(tmpl.render(**tmpl_param))
