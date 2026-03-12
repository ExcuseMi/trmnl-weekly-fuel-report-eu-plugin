function transform(input) {
  const country = input.country;
  const overview = input.overview;
  
  // Clean up values for easier Liquid access
  const data = {
    name: country.name,
    last_updated: country.last_updated,
    petrol: country.fuel.euro_95_petrol.eur_per_l.value,
    petrol_change: country.fuel.weekly_change.petrol.value,
    diesel: country.fuel.diesel.eur_per_l.value,
    diesel_change: country.fuel.weekly_change.diesel.value,
    trend: country.fuel.trend_e95.map(p => p.value),
    inflation: country.economics.inflation_rate.value,
    electricity: country.economics.electricity_price.value,
    work_hours: country.economics.tank_50l.labor_hours.value,
    eu_avg_petrol: overview['EU Average Euro 95 Petrol'].value,
    eu_avg_diesel: overview['EU Average Diesel'].value
  };

  return { data };
}
