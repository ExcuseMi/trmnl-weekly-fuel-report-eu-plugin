function transform(input) {
  const country = input.country;
  const overview = input.overview;
  
  const petrol = country.fuel.euro_95_petrol.eur_per_l.value;
  const diesel = country.fuel.diesel.eur_per_l.value;
  const eu_avg_petrol = overview['EU Average Euro 95 Petrol'].value;
  const eu_avg_diesel = overview['EU Average Diesel'].value;

  const petrol_pct = Math.round((petrol / eu_avg_petrol) * 100);
  const diesel_pct = Math.round((diesel / eu_avg_diesel) * 100);

  const code = (country.country_code || "EU").toLowerCase();
  
  // Safely access economics data with fallbacks
  const inflation = country.economics?.inflation_rate?.value ?? null;
  const electricity = country.economics?.electricity_price?.value ?? null;
  const work_hours = country.economics?.tank_50l?.labor_hours?.value ?? null;
  const tank_cost = country.economics?.tank_50l?.cost?.value ?? null;

  const data = {
    name: country.name,
    code: code.toUpperCase(),
    flag_url: `https://flagcdn.com/w320/${code}.png`,
    map_url: `https://raw.githubusercontent.com/djaiss/mapsicon/master/all/${code}/1024.png`,
    last_updated: country.last_updated,

    petrol: petrol,
    petrol_change: country.fuel.weekly_change.petrol.value,
    petrol_pct: petrol_pct,

    diesel: diesel,
    diesel_change: country.fuel.weekly_change.diesel.value,
    diesel_pct: diesel_pct,

    trend: country.fuel.trend_e95.map(p => p.value),
    inflation: inflation,
    electricity: electricity,
    work_hours: work_hours,
    tank_cost: tank_cost,

    eu_avg_petrol: eu_avg_petrol,
    eu_avg_diesel: eu_avg_diesel,
    fetched_at: new Date().toISOString()
  };

  return { data };
}