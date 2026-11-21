const MODEL_FEATURE_LABELS: Record<string, string> = {
  nocar_pct: 'Car-free households', stops_per_1k: 'Stops per 1,000 people',
  nonwhite_pct: 'Non-White population share', disability_pct: 'Disability share',
  income_score: 'Income deprivation score', elderly_pct: 'Elderly population share',
  imd_score: 'IMD score', unemployment_rate: 'Unemployment rate', urban_enc: 'Urban indicator',
  fedi_score: 'F-EDI score', hp_relative: 'Pobal HP score', ses_woa: 'SES-WOA',
}

export const modelFeatureLabel = (name: string) => MODEL_FEATURE_LABELS[name] ?? name.replaceAll('_', ' ')
