import csv
import argparse
import logging
import requests
from urllib.parse import quote
from datetime import datetime
from predictor import Predictor

PREDICTOR = Predictor('models/')
now = datetime.now()
script_start = now.strftime("%Y%m%d_%H%M%S")
logging.basicConfig(filename=f'{script_start}_ensemble_test.log', level=logging.ERROR, format='%(asctime)s %(levelname)s %(message)s')


def query_affiliation(affiliation):
    try:
        chosen_id = None
        score = None
        url = "https://api.ror.org/organizations"
        params = {"affiliation": affiliation}
        r = requests.get(url, params=params)
        api_response = r.json()
        results = api_response['items']
        if results:
            for result in results:
                if result['chosen']:
                    chosen_id = result['organization']['id']
                    score = result['score']
    except Exception as e:
        logging.error(f'Error for query: {affiliation} - {e}')
    return chosen_id, score


def ensemble_match(affiliation, min_fasttext_probability=0.8, match_order='fasttext'):
    if match_order == 'fasttext':
        fasttext_ror_id, fasttext_probability = PREDICTOR.predict_ror_id(
            affiliation, min_fasttext_probability)
        if fasttext_ror_id:
            return fasttext_ror_id, fasttext_probability
        else:
            ror_aff_predicted_id, ror_aff_score = query_affiliation(
                affiliation)
            return ror_aff_predicted_id, ror_aff_score
    else:
        ror_aff_predicted_id, ror_aff_score = query_affiliation(affiliation)
        if ror_aff_predicted_id:
            return ror_aff_predicted_id, ror_aff_score
        else:
            fasttext_ror_id, fasttext_probability = PREDICTOR.predict_ror_id(
                affiliation, min_fasttext_probability)
            return fasttext_ror_id, fasttext_probability


def parse_and_query(input_file, output_file, min_fasttext_probability, match_order):
    try:
        with open(input_file, 'r+', encoding='utf-8-sig') as f_in, open(output_file, 'w') as f_out:
            reader = csv.DictReader(f_in)
            fieldnames = reader.fieldnames + \
                ["prediction", "probability", "match"]
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            for row in reader:
                affiliation = row['affiliation']
                predicted_id, prediction_score = ensemble_match(
                    affiliation, min_fasttext_probability, match_order)
                match = 'Y' if predicted_id and predicted_id == row['ror_id'] else (
                    'NP' if not predicted_id else 'N')
                row.update({
                    "prediction": predicted_id,
                    "probability": prediction_score,
                    "match": match
                })
                writer.writerow(row)
    except Exception as e:
        logging.error(f'Error in parse_and_query: {e}')


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Return ensemble (ROR affiliation + fasttext) matches for a given CSV file.')
    parser.add_argument('-i', '--input', help='Input CSV file', required=True)
    parser.add_argument('-o', '--output', help='Output CSV file',
                        default='ensemble_results.csv')
    parser.add_argument(
        '-p', '--min_fasttext_probability', help='min_fasttext_probability level for the fasttext predictor', type=float, default=0.8)
    parser.add_argument('-m', '--match_order', choices=['fasttext', 'affiliation'],
                        help='Order of matching methods ("fasttext" or "affiliation")', default='fasttext')
    return parser.parse_args()


def main():
    args = parse_arguments()
    parse_and_query(args.input, args.output,
                    args.min_fasttext_probability, args.match_order)


if __name__ == '__main__':
    main()
