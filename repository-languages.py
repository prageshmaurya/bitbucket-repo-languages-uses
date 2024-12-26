import os
from git import Repo
import pandas as pd
from atlassian.bitbucket import Cloud
import ghlinguist as ghl

# Bitbucket workspace
WORKSPACE = "example"  # Provide the workspace name


# Function to authenticate using the Bitbucket package (using App password or OAuth token)
def get_authenticated_session(username, app_password):
    # Create an instance of the Bitbucket API client
    cloud = Cloud(username=username, password=app_password, cloud=True)
    bitbucket = cloud.workspaces.get(WORKSPACE)
    return bitbucket


# Function to get the list of repositories in a Bitbucket project using the project key
def get_repositories_in_project(bitbucket, project_key):
    repositories = []
    try:
        # Fetch the repositories for a project using the project key
        project = bitbucket.projects.get(project_key)
        repos = project.repositories.each()
        for repo in repos:
            repositories.append(repo.slug)

    except Exception as e:
        print(f"Failed to fetch repositories: {e}")
    return repositories


# Function to clone a Bitbucket repository
def clone_bitbucket_repo(username, password, repo_slug, clone_dir):
    repo_url = f'https://{username}:{password}@bitbucket.org/{username}/{repo_slug}.git'
    try:
        print(f"Cloning repository {repo_slug} from Bitbucket...")
        # Clone the Bitbucket repository using GitPython
        Repo.clone_from(repo_url, clone_dir)
        print(f"Repository {repo_slug} cloned successfully.")
    except Exception as e:
        print(f"Failed to clone the repository: {e}")


# Function to analyze languages using github-linguist
def analyze_languages_with_linguist(clone_dir):
    try:
        # Analyze the repository in the cloned directory
        print("Analyzing languages using github-linguist...")
        language_stats = ghl.linguist(clone_dir)

        # Convert the list of tuples to a dictionary (if it's a list)
        if isinstance(language_stats, list):
            language_stats = {lang: perc for lang, perc in language_stats}

        return language_stats
    except Exception as e:
        print(f"Error while analyzing the repository with github-linguist: {e}")
        return {}


# Function to create and save the Excel file with the results
def save_to_excel(project_languages, overall_languages, output_file):
    # Create a Pandas Excel writer using openpyxl as the engine
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Write each project's language analysis to a separate sheet
        for project_name, repo_languages in project_languages.items():
            # Create a list of repositories
            repo_slugs = list(repo_languages.keys())
            
            # Get the union of all languages across repositories in the project
            all_languages = set()
            for repo_langs in repo_languages.values():
                all_languages.update(repo_langs.keys())
            
            # Prepare a DataFrame to hold the language statistics
            project_data = []
            
            for repo_slug in repo_slugs:
                repo_langs = repo_languages[repo_slug]
                # Create a row for the repository with missing languages filled with NaN
                row = {lang: repo_langs.get(lang, 0) for lang in all_languages}
                row['Repository'] = repo_slug
                project_data.append(row)
            
            # Convert to DataFrame, ensuring all repositories and languages align
            project_df = pd.DataFrame(project_data)
            project_df.set_index('Repository', inplace=True)

            # Write the DataFrame to the Excel file, one sheet per project
            project_df.to_excel(writer, sheet_name=project_name)

        # Write the overall language usage summary to a new sheet
        overall_df = pd.DataFrame(list(overall_languages.items()), columns=['Language', 'Percentage'])
        overall_df.set_index('Language', inplace=True)
        overall_df.to_excel(writer, sheet_name="Overall Summary")


# Main function
def main():
    # Replace with your Bitbucket credentials and project/repository info
    bitbucket_username = os.getenv("BB_USER")  # Set environment variable BB_USER to provide the Bitbucket username
    bitbucket_app_password = os.getenv("BB_APP_PASSWORD")  # Set environment variable BB_APP_PASSWORD to provide the Bitbucket app password
    bitbucket_project_keys = ["ABC", "XYZ"]  # Replace with your Bitbucket project keys
    output_excel_file = "project_languages.xlsx"  # Output Excel file path

    # Get authenticated session using the Bitbucket package
    bitbucket = get_authenticated_session(bitbucket_username, bitbucket_app_password)

    # Dictionary to hold the language analysis for each project
    project_languages = {}
    overall_languages = {}

    for project_key in bitbucket_project_keys:
        # Get the list of repositories in the current Bitbucket project using project key
        repositories = get_repositories_in_project(bitbucket, project_key)

        if repositories:
            repo_languages = {}

            for repo_slug in repositories:
                # Create a directory for the cloned repo
                clone_dir = f"/tmp/repos/cloned_repo_{repo_slug}"

                # Clone the repository
                clone_bitbucket_repo(bitbucket_username, bitbucket_app_password, repo_slug, clone_dir)

                # Analyze the repository using github-linguist
                language_stats = analyze_languages_with_linguist(clone_dir)

                # Add the results for the repository
                repo_languages[repo_slug] = language_stats

                # Accumulate the language stats in the overall dictionary
                for language, percentage in language_stats.items():
                    if language in overall_languages:
                        overall_languages[language] += float(percentage)
                    else:
                        overall_languages[language] = float(percentage)

                # Optionally, clean up the cloned repository after analysis
                os.system(f"rm -rf {clone_dir}")  # Uncomment to delete the cloned repository after analysis

            # Store the repository languages for the current project
            project_languages[project_key] = repo_languages
        else:
            print(f"No repositories found for project {project_key}.")

    # Normalize the overall language percentages
    total_percentage = 0
    for value in overall_languages.values():
        total_percentage += value
    for language in overall_languages:
        overall_languages[language] = (overall_languages[language] / total_percentage) * 100

    # Save the results to an Excel file
    save_to_excel(project_languages, overall_languages, output_excel_file)
    print(f"Language analysis saved to {output_excel_file}")


if __name__ == "__main__":
    main()
