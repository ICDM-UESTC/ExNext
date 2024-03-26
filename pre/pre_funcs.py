import pandas as pd
from typing import Dict, Tuple
from sklearn.preprocessing import LabelEncoder
import logging

#remove the samples of validate and test if those POIs or users didnt show in training samples
def remain_available(df: pd.DataFrame) -> Dict:
    preprocess_result = dict()
    df_train = df[df['SplitTag'] == 'train']
    df_validate = df[df['SplitTag'] == 'validation']
    df_test = df[df['SplitTag'] == 'test']

    train_user_set = set(df_train['UserId'])
    train_poi_set = set(df_train['PoiId'])
    df_validate = df_validate[
        (df_validate['UserId'].isin(train_user_set)) & (df_validate['PoiId'].isin(train_poi_set))].reset_index()
    df_test = df_test[(df_test['UserId'].isin(train_user_set)) & (df_test['PoiId'].isin(train_poi_set))].reset_index()

    preprocess_result['sample'] = df
    preprocess_result['train_sample'] = df_train
    preprocess_result['validate_sample'] = df_validate
    preprocess_result['test_sample'] = df_test

    logging.info(
        f"[Preprocess] train shape: {df_train.shape}, validation shape: {df_validate.shape}, "
        f"test shape: {df_test.shape}"
    )
    return preprocess_result

def encodeID(
        fit_df: pd.DataFrame,
        encode_df: pd.DataFrame,
        column: str,
        padding: int = -1
) -> Tuple[LabelEncoder, int]:
    """
    :param fit_df: only consider the data in encode df for constructing LabelEncoder instance
    :param encode_df: the dataframe which use the constructed LabelEncoder instance to encode their values
    :param column: the column to be encoded
    :param padding:
    :return:
    """
    id_mapping = {value: index for index, value in enumerate(fit_df[column].unique())}
    if padding == 0:
        padding_id = padding
        encode_df[column] = [id_mapping[i] + 1 if i in id_mapping else padding_id for i in encode_df[column].values.tolist()]
    else:
        padding_id = len(id_mapping)
        encode_df[column] = [id_mapping[i] if i in id_mapping else padding_id for i in encode_df[column].values.tolist()]
    id_le = LabelEncoder()
    return id_le, padding_id

#Ignore the first check-in sample of every trajectory because of no historical check-in.
def dropfirst(df: pd.DataFrame) -> pd.DataFrame:
    df['pseudo_session_trajectory_rank'] = df.groupby(
        'pseudo_session_trajectory_id')['UTCTimeOffset'].rank(method='first')
    df['query_pseudo_session_trajectory_id'] = df['pseudo_session_trajectory_id'].shift()
    df.loc[df['pseudo_session_trajectory_rank'] == 1, 'query_pseudo_session_trajectory_id'] = None
    df['last_checkin_epoch_time'] = df['UTCTimeOffsetEpoch'].shift()
    df.loc[df['pseudo_session_trajectory_rank'] == 1, 'last_checkin_epoch_time'] = None
    df.loc[df['UserRank'] == 1, 'SplitTag'] = 'ignore'
    df.loc[df['pseudo_session_trajectory_rank'] == 1, 'SplitTag'] = 'ignore'
    return df

#Only keep the last check-in samples in validation and testing for measuring model performance.
def keeplast(df: pd.DataFrame) -> pd.DataFrame:
    df['pseudo_session_trajectory_count'] = df.groupby(
        'pseudo_session_trajectory_id')['UTCTimeOffset'].transform('count')
    df.loc[(df['SplitTag'] == 'validation') & (
            df['pseudo_session_trajectory_count'] != df['pseudo_session_trajectory_rank']
    ), 'SplitTag'] = 'ignore'
    df.loc[(df['SplitTag'] == 'test') & (
            df['pseudo_session_trajectory_count'] != df['pseudo_session_trajectory_rank']
    ), 'SplitTag'] = 'ignore'

    return df
