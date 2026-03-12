import requests
import re
import json
import os
import argparse

def clean_num(text):
    if not text: return None
    cleaned = re.sub(r"[^\d.-]", "", text.replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None

def parse_value_unit(text):
    if not text: return text
    if isinstance(text, dict): return text
    
    # Currency
    curr_match = re.search(r"(€|EUR|€/L|€/kWh)\s*([\d,.]+)", text)
    if curr_match:
        val = clean_num(curr_match.group(2))
        unit = "EUR"
        if "/L" in text or "per liter" in text: unit = "EUR/L"
        elif "/kWh" in text: unit = "EUR/kWh"
        return {"value": val, "unit": unit}

    # Percentages
    pc_match = re.search(r"([+-]?[\d.-]+)%", text)
    if pc_match:
        return {"value": clean_num(pc_match.group(1)), "unit": "percent"}

    # Hours
    hr_match = re.search(r"([\d.]+)\s*hours", text)
    if hr_match:
        return {"value": clean_num(hr_match.group(1)), "unit": "hours"}

    return text

def parse_trend(text):
    """Parses '1.453 → 1.455 → 1.480' into a list of value objects."""
    parts = text.split("→")
    trend = []
    for p in parts:
        val = clean_num(p.strip())
        if val is not None:
            trend.append({"value": val, "unit": "EUR/L"})
    return trend

def parse_weekly_change(text):
    """Parses 'Petrol +12.74%, Diesel +21.36%'."""
    res = {}
    p_match = re.search(r"Petrol\s+([+-][\d.]+)%", text)
    if p_match:
        res["petrol"] = {"value": float(p_match.group(1)), "unit": "percent"}
    d_match = re.search(r"Diesel\s+([+-][\d.]+)%", text)
    if d_match:
        res["diesel"] = {"value": float(d_match.group(1)), "unit": "percent"}
    return res

def parse_fuel_prices_txt(url="https://www.fuel-prices.eu/llms-full.txt"):
    try:
        response = requests.get(url)
        response.raise_for_status()
        content = response.text
    except Exception as e:
        return {"error": f"Failed to fetch data: {str(e)}"}

    data = {
        "metadata": {},
        "overview": {},
        "current_prices": [],
        "country_profiles": {},
    }

    current_section = None
    current_country = None
    in_table = False
    
    lines = content.splitlines()

    for line in lines:
        line = line.strip()
        if not line: continue

        if line.startswith("## "):
            header = line[3:].strip()
            in_table = False
            current_country = None
            if "METADATA" in header: current_section = "metadata"
            elif "EU FUEL PRICE OVERVIEW" in header: current_section = "overview"
            elif "CURRENT FUEL PRICES" in header: current_section = "current_prices"
            elif "DETAILED COUNTRY PROFILES" in header: current_section = "country_profiles"
            else: current_section = None
            continue

        if line.startswith("### "):
            match = re.match(r"### (.+?)(?: \(([A-Z]{2})\))?$", line)
            if match:
                current_country = match.group(2) if match.group(2) else match.group(1)
                if current_section == "country_profiles" and match.group(2):
                    data["country_profiles"][current_country] = {
                        "name": match.group(1),
                        "country_code": current_country,
                        "fuel": {},
                        "economics": {},
                        "road_costs": {}
                    }
            continue

        if current_section in ["metadata", "overview"]:
            if ":" in line:
                key, value = map(str.strip, line.split(":", 1))
                data[current_section][key] = parse_value_unit(value)
        
        elif current_section == "current_prices":
            if line.startswith("---"):
                in_table = True
                continue
            if in_table:
                match = re.search(r"^([A-Z]{2})\s+(.*?)\s+€\s+([\d.]+)\s+€\s+([\d.]+)\s+([+-][\d.]+%)\s+([+-][\d.]+%|None)?", line)
                if match:
                    data["current_prices"].append({
                        "country_code": match.group(1),
                        "country_name": match.group(2).strip(),
                        "euro95": {"value": float(match.group(3)), "unit": "EUR/L"},
                        "diesel": {"value": float(match.group(4)), "unit": "EUR/L"},
                        "euro95_vs_avg": parse_value_unit(match.group(5)),
                        "diesel_vs_avg": parse_value_unit(match.group(6)) if match.group(6) else None
                    })

        elif current_section == "country_profiles" and current_country:
            if ":" in line:
                key, value = map(str.strip, line.split(":", 1))
                key_clean = re.sub(r"^[-\s]+", "", key)
                if not value: continue
                
                # Fuel Section
                if any(x in key_clean for x in ["Euro 95", "Diesel", "Weekly change", "vs EU average", "Recent trend"]):
                    if "Weekly change" in key_clean:
                        data["country_profiles"][current_country]["fuel"]["weekly_change"] = parse_weekly_change(value)
                    elif "Recent trend" in key_clean:
                        data["country_profiles"][current_country]["fuel"]["trend_e95"] = parse_trend(value)
                    elif "vs EU average" in key_clean:
                        data["country_profiles"][current_country]["fuel"]["vs_eu_avg"] = parse_value_unit(value)
                    else:
                        # Price detail (€1.708/L (€6.47 per US gallon))
                        m = re.search(r"€\s*([\d.]+)/L\s*\(€\s*([\d.]+)", value)
                        data["country_profiles"][current_country]["fuel"][key_clean.lower().replace(" ", "_")] = {
                            "eur_per_l": {"value": float(m.group(1)), "unit": "EUR/L"} if m else None,
                            "eur_per_gal": {"value": float(m.group(2)), "unit": "EUR/gal"} if m else None
                        }
                
                # Economics Section
                elif any(x in key_clean for x in ["wage", "tank cost", "Electricity", "Inflation"]):
                    if "50L tank cost" in key_clean:
                        m = re.match(r"(€[\d.]+)\s*\(([\d.]+)\s*hours", value)
                        data["country_profiles"][current_country]["economics"]["tank_50l"] = {
                            "cost": parse_value_unit(m.group(1)) if m else parse_value_unit(value),
                            "labor_hours": {"value": float(m.group(2)), "unit": "hours"} if m else None
                        }
                    else:
                        data["country_profiles"][current_country]["economics"][key_clean.lower().replace(" ", "_")] = parse_value_unit(value)
                
                # Road Costs (Vignettes/Tolls)
                else:
                    data["country_profiles"][current_country]["road_costs"][key_clean] = parse_value_unit(value)

            elif line.startswith("- "):
                if "notes" not in data["country_profiles"][current_country]:
                    data["country_profiles"][current_country]["notes"] = []
                data["country_profiles"][current_country]["notes"].append(line[2:].strip())

    return data

def main():
    parser = argparse.ArgumentParser(description="Parse fuel-prices.eu data to highly structured JSON.")
    parser.add_argument("-o", "--output", default="data/data.json", help="Output path (full dump)")
    args = parser.parse_args()
    
    result = parse_fuel_prices_txt()
    if "error" in result:
        print(result["error"])
        return
        
    data_dir = os.path.dirname(args.output)
    os.makedirs(data_dir, exist_ok=True)
    
    # Save full dump
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Save per-country files
    for cc, profile in result["country_profiles"].items():
        # Only process actual country codes
        if len(cc) == 2 and cc.isupper():
            country_data = {
                "metadata": result["metadata"],
                "overview": result["overview"],
                "country": profile
            }
            country_path = os.path.join(data_dir, f"{cc}.json")
            with open(country_path, "w", encoding="utf-8") as f:
                json.dump(country_data, f, indent=2, ensure_ascii=False)

    print(f"Successfully saved {len(result['country_profiles'])} files to {data_dir}")

if __name__ == "__main__":
    main()
