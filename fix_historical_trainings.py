import csv
import os

def manual_data():
    data = {
        2022: [
            ["Mastering Plone 6", "Philip Bauer; Katja Süss", "Starzel; Rohberg"],
            ["Plone 6 Classic UI Theming", "Maik Derstappen; Stefan Antonelli", "Derico; Kombinat"],
            ["Installing Plone", "Érico Andrei; Jens Klein", "kitconcept GmbH; Klein & Partner KG"],
            ["Volto and React", "Alok Kumar; Jakob Kahl", "kitconcept GmbH; kitconcept GmbH"],
            ["Learn Plone, for Content Editors and Managers", "Kim Nguyen; Kim Paulissen", "Six Feet Up; KU Leuven"],
            ["Use, Integrate and develop Patterns for Plone 6 Classic", "Johannes Raggam", "Independent"],
            ["Effective Volto", "Tiberiu Ichim; Victor Fernandez de Alba", "Eau de Web; kitconcept GmbH"],
            ["Migration training", "Philip Bauer", "Starzel"]
        ],
        2021: [
            ["Mastering Plone 6", "Philip Bauer; Katja Süss", "Starzel; Rohberg"],
            ["Volto Add-ons", "Tiberiu Ichim; Victor Fernandez de Alba", "Eau de Web; kitconcept GmbH"],
            ["React", "Alok Kumar; Jakob Kahl", "kitconcept GmbH; kitconcept GmbH"],
            ["Plone 6 Classic UI Theming", "Maik Derstappen; Stefan Antonelli", "Derico; Kombinat"],
            ["Plone Deployment", "Érico Andrei", "kitconcept GmbH"],
            ["Gatsby with Plone", "Victor Fernandez de Alba", "kitconcept GmbH"]
        ],
        2020: [
            ["Mastering Plone 6", "Katja Süss; Philip Bauer", "Rohberg; Starzel"],
            ["Volto Addons", "Tiberiu Ichim; Victor Fernandez de Alba", "Eau de Web; kitconcept GmbH"],
            ["React and Volto", "Alok Kumar; Jakob Kahl", "kitconcept GmbH; kitconcept GmbH"],
            ["Pyramid", "Steve Piercy", "Steve Piercy - Website Builder"],
            ["Getting started with your Plone site", "Kim Nguyen", "Six Feet Up"],
            ["Guillotina", "Nathan Van Gheem", "Wildcard"]
        ]
    }
    
    os.makedirs('data/community-contributions', exist_ok=True)
    for year, trainings in data.items():
        output_file = f'data/community-contributions/{year}-plone-conference-trainings.csv'
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Title', 'Trainer(s)', 'Organisation'])
            for t in trainings:
                writer.writerow(t)
        print(f"Created {output_file}")

if __name__ == "__main__":
    manual_data()
