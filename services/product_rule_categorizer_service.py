import re
from typing import Any
from models import Category
from services.excel_price_service import clean_product_name

# Core category rule definitions mapping category archetype names to regex patterns / keywords
CATEGORY_RULES: dict[str, list[str]] = {
    "Toys": [
        r"\btoy\b", r"\btoys\b", r"\bcar(?!\s+(charger|perfume|air|freshener))\b", r"\bcars\b", r"\bsport\s*car\b", r"\btrain\b",
        r"\bdoll\b", r"\bdolls\b", r"\blego\b", r"\bpuzzle\b", r"\bgame\b", r"\bgames\b",
        r"\brobot\b", r"\bdance\s*hero\b", r"\bsuper\s*hero\b", r"\bhero\b", r"\bdrone\b",
        r"\brc\b", r"\bdiecast\b", r"\baction\s*figure\b", r"\bplay\s*set\b", r"\bplayset\b",
        r"\bstuffed\b", r"\bteddy\b", r"\bplush\b", r"\bwater\s*gun\b", r"\bbubble\s*gun\b",
        r"\bballoon\b", r"\bballoons\b", r"\bplaydough\b", r"\bclay\b", r"\brattle\b",
        r"\bmagic\s*track\b", r"\bblock\s*set\b", r"\bbuilding\s*block\b", r"\bboard\s*game\b",
        r"\bludo\b", r"\bchess\b", r"\bcarrom\b", r"\bslime\b", r"\bfidget\b", r"\bspinner\b",
        r"\bhelicopter\b", r"\bairplane\b", r"\btruck\b", r"\bjeep\b", r"\bbike\b", r"\bcycle\b",
        r"\banimal\b", r"\banimals\b", r"\bzoo\b", r"\bdinosaur\b", r"\bdino\b", r"\bgun\b",
        r"\bguns\b", r"\bfigure\b", r"\bfigures\b", r"\bcollection\b", r"\bmodel\b", r"\bracing\b",
    ],
    "Beverages": [
        r"\btea(?!\s+(poni|strainer|cup|mug|spoon|maker))\b", r"\bchai(?!\s+(poni|strainer|cup|mug|spoon|maker|channi))\b", r"\bgreen\s*tea\b", r"\bblack\s*tea\b", r"\bcoffee(?!\s+(maker|mug|cup|machine))\b",
        r"\bnescafe\b", r"\bjuice(?!\s+(maker|machine|extractor))\b", r"\bjuices\b", r"\bnectar\b", r"\bdrink\b", r"\bdrinks\b",
        r"\bcola\b", r"\bpepsi\b", r"\bcoke\b", r"\bnestle\b", r"\bnext\s*cola\b", r"\bcoca\s*cola\b", r"\bsprite\b", r"\b7up\b",
        r"\bfanta\b", r"\bdew\b", r"\bmountain\s*dew\b", r"\bmirinda\b", r"\bwater(?!\s+(gun|bottle|cooler|dispenser|set|glass|jug|filter))\b",
        r"\bmineral\s*water\b", r"\benergy\s*drink\b", r"\bred\s*bull\b", r"\bsting\b",
        r"\btang\b", r"\brooh\s*afza\b", r"\bjam-e-shirin\b", r"\bsquash\b", r"\bsyrup\b",
        r"\bsoda\b", r"\blemonade\b", r"\bmilkshake\b", r"\bshake\b", r"\bmilo\b", r"\bhorlicks\b",
        r"\bcomplan\b", r"\bcan\s*330ml\b", r"\bcan\s*250ml\b", r"\b1\.5ltr\b", r"\b2\.25ltr\b",
    ],
    "Dairy & Eggs": [
        r"\bmilk\b", r"\byogurt\b", r"\byoghurt\b", r"\bdahi\b", r"\bbutter\b", r"\bmakhan\b",
        r"\bcheese\b", r"\bghee\b", r"\bdesi\s*ghee\b", r"\bcream\b", r"\bmalai\b",
        r"\bpaneer\b", r"\begg(?!\s+(beater|cutter|slicer|tray|boiler))\b", r"\beggs(?!\s+(beater|cutter|slicer|tray|boiler))\b", r"\banday\b", r"\bcondensed\s*milk\b",
        r"\buht\b", r"\btetra\s*pack\b", r"\bolper\b", r"\bolpers\b", r"\bmilkpak\b",
        r"\bnurpur\b", r"\btara\b", r"\beveryday\b", r"\bnido\b", r"\bcheddar\b", r"\bmozzarella\b",
    ],
    "Bakery & Bread": [
        r"\bbread(?!\s+(box|knife|maker))\b", r"\bbun\b", r"\bbuns\b", r"\brusk\b", r"\brusks\b", r"\bcake(?!\s+(pan|set|stand|base))\b",
        r"\bcakes\b", r"\bcupcake\b", r"\bpastry\b", r"\bpastries\b", r"\bcroissant\b",
        r"\bmuffin\b", r"\bmuffins\b", r"\bbiscuit\b", r"\bbiscuits\b", r"\bcookie\b",
        r"\bcookies\b", r"\btoast\b", r"\bnaan\b", r"\broti\b", r"\bsheermal\b", r"\btaftan\b",
        r"\bbakery\b", r"\bcracker\b", r"\bcrackers\b", r"\bwafer\b", r"\bwafers\b",
    ],
    "Snacks & Confectionery": [
        r"\bchips\b", r"\bcrisps\b", r"\bkurkure\b", r"\blays\b", r"\bwavy\b", r"\bnimko\b",
        r"\bpopcorn\b", r"\bchocolate\b", r"\bchocolates\b", r"\bcandy\b", r"\bcandies\b",
        r"\btoffee\b", r"\btoffees\b", r"\bbubble\s*gum\b", r"\bgum(?!\s+(uhu|stick|nail))\b", r"\blollipop\b",
        r"\blollipops\b", r"\bsnack\b", r"\bsnacks\b", r"\bmarshmallow\b", r"\bcaramel\b",
        r"\bsweets\b", r"\bmithai\b", r"\bslanty\b", r"\bcheetos\b", r"\bdoritos\b",
        r"\bkitkat\b", r"\bdairy\s*milk\b", r"\bsnickers\b", r"\bmars\b", r"\bbounty\b",
        r"\btoblerone\b", r"\bferrero\b", r"\bnutella\b", r"\bgellies\b", r"\bjelly\b",
    ],
    "Grocery & Staples": [
        r"\brice\b", r"\bbasmati\b", r"\bflour\b", r"\batta\b", r"\bmaida\b", r"\bsooji\b",
        r"\bbesan\b", r"\bpulse\b", r"\bpulses\b", r"\bdaal\b", r"\bdal\b", r"\blentil\b",
        r"\blentils\b", r"\bchana\b", r"\bmoong\b", r"\bmasoor\b", r"\bmash\b", r"\blobiya\b",
        r"\bsugar\b", r"\bcheeni\b", r"\bsalt\b", r"\bnamak\b", r"\boil\b", r"\bcooking\s*oil\b",
        r"\bcanola\b", r"\bsunflower\b", r"\bbanaspati\b", r"\bspices\b",
        r"\bmasala\b", r"\bmirch\b", r"\bturmeric\b", r"\bhaldi\b", r"\bcoriander\b",
        r"\bdhaniya\b", r"\bzeera\b", r"\bcumin\b", r"\bclove\b", r"\blaung\b", r"\bcardamom\b",
        r"\belaichi\b", r"\bcinnamon\b", r"\bdarchini\b", r"\bblack\s*pepper\b", r"\bvinegar\b",
        r"\bsirca\b", r"\bsoy\s*sauce\b", r"\bchilli\s*sauce\b", r"\bketchup\b", r"\bmayonnaise\b",
        r"\bmayo\b", r"\bpasta\b", r"\bmacaroni\b", r"\bnoodles\b", r"\bvermicelli\b",
        r"\bsewaiyan\b", r"\bspaghetti\b", r"\bsoup\b", r"\bknorr\b", r"\bmaggi\b",
        r"\bnational\b", r"\bshan\b", r"\bhabib\b", r"\bmeezan\b", r"\bdalda\b", r"\bsufi\b",
    ],
    "Personal Care": [
        r"\blip\s*stick\b", r"\blip\s*pencil\b", r"\beye\s*pencil\b", r"\bnail\s*gum\b", r"\btissue\s*box\b",
        r"\bsoap\b", r"\bsoaps\b", r"\bhand\s*wash\b", r"\bhandwash\b", r"\bshampoo\b",
        r"\bconditioner\b", r"\blotion\b", r"\bbody\s*lotion\b", r"\bcream\b", r"\bface\s*cream\b",
        r"\bface\s*wash\b", r"\bfacewash\b", r"\bbody\s*wash\b", r"\bshower\s*gel\b",
        r"\bperfume\b", r"\bdeodorant\b", r"\bbody\s*spray\b", r"\bbodyspray\b",
        r"\btooth\s*paste\b", r"\btoothpaste\b", r"\btoothbrush\b", r"\btooth\s*brush\b",
        r"\brazor\b", r"\bblade\b", r"\bblades\b", r"\bshaving\b", r"\bgillette\b",
        r"\bsanitary\b", r"\bpad\b", r"\bpads\b", r"\bdiaper\b", r"\bdiapers\b", r"\bpampers\b",
        r"\bbaby\s*wipes\b", r"\bwipes\b", r"\btissue\b", r"\btissues\b", r"\bcotton\b",
        r"\bhair\s*oil\b", r"\blip\s*balm\b", r"\bsunscreen\b", r"\bdove\b", r"\blux\b",
        r"\blifebuoy\b", r"\bsafeguard\b", r"\bpalmolive\b", r"\bsunsilk\b", r"\bpantene\b",
        r"\bhead\s*&\s*shoulders\b", r"\bcolgate\b", r"\bsensodyne\b", r"\bclose\s*up\b",
    ],
    "Household & Cleaning": [
        r"\bdetergent\b", r"\bwashing\s*powder\b", r"\bsurf\b", r"\bsurf\s*excel\b",
        r"\bariel\b", r"\bbonus\b", r"\bexpress\b", r"\bbrite\b", r"\bsoap\s*bar\b",
        r"\bdishwash\b", r"\bdish\s*wash\b", r"\bvim\b", r"\bmax\b", r"\blemon\s*max\b",
        r"\bcleaner\b", r"\bfloor\s*cleaner\b", r"\btp\s*cleaner\b", r"\bharpic\b",
        r"\bbleach\b", r"\brobin\b", r"\bphenyl\b", r"\bmop\b", r"\bbroom\b", r"\bsponge\b",
        r"\bscrubber\b", r"\bscourer\b", r"\bair\s*freshener\b", r"\binsect\s*spray\b",
        r"\bmortein\b", r"\bking\s*tox\b", r"\bbattery\b", r"\bbatteries\b", r"\bcell\b",
        r"\bcells\b", r"\bfoil\b", r"\baluminium\s*foil\b", r"\bcling\s*film\b",
        r"\bgarbage\s*bag\b", r"\btrash\s*bag\b", r"\bshopper\b", r"\bliquid\s*bleach\b",
        r"\bcomfort\b", r"\bdowny\b", r"\bfabric\s*softener\b", r"\bmatch\s*box\b", r"\bmatches\b",
        r"\bpeeler\b", r"\bpan\b", r"\bsauce\s*pan\b", r"\bfry\s*pan\b", r"\bpot\b",
        r"\bstrainer\b", r"\bponi\b", r"\bchanni\b", r"\bjuicer\b", r"\bblender\b",
        r"\bchopper\b", r"\bknife\b", r"\bknives\b", r"\bspoon\b", r"\bspoons\b", r"\bfork\b",
        r"\bplate\b", r"\bplates\b", r"\bbowl\b", r"\bbowls\b", r"\bmug\b", r"\bcup\b",
        r"\bcups\b", r"\bglass\b", r"\bglasses\b", r"\bjug\b", r"\bflask\b", r"\bthermos\b",
        r"\bdustbin\b", r"\bbottle\b", r"\biron\s*stand\b", r"\bwiper\b",
    ],
    "Meat & Seafood": [
        r"\bchicken(?!\s+(karahi|masala|powder))\b", r"\bbeef\b", r"\bmutton\b", r"\bmeat(?!\s+(hammer|hamer|mincer|tenderizer))\b", r"\bfish\b", r"\bprawn\b",
        r"\bprawns\b", r"\bseafood\b", r"\bmince\b", r"\bkeema\b", r"\bqeema\b", r"\bwings\b",
        r"\bdrumstick\b", r"\bdrumsticks\b", r"\bnuggets\b", r"\bkabab\b", r"\bkebab\b",
        r"\bpatty\b", r"\bpatties\b", r"\bsausage\b", r"\bsausages\b", r"\bsalami\b",
        r"\bk&n\b", r"\bknns\b", r"\bmenu\b", r"\bmon\s*salwa\b", r"\bseasons\b",
    ],
    "Fruits & Vegetables": [
        r"\bapple(?!\s+(juicer|vinegar|cider|watch|phone|iphone|mac|ipad))\b", r"\bbanana\b", r"\bmango\b", r"\borange\b", r"\bcitrus\b", r"\bpotato(?!\s+(masher|peeler|cutter))\b",
        r"\baloo(?!\s+(samosa|roll|paratha))\b", r"\bonion\b", r"\bpyaz\b", r"\btomato\b", r"\btamatar\b", r"\bginger\b",
        r"\badrak\b", r"\bgarlic\b", r"\blehsan\b", r"\blemon\b", r"\bleemu\b", r"\bchili\b",
        r"\bmirchi\b", r"\bcoriander\b", r"\bdhaniya\b", r"\bmint\b", r"\bpudina\b",
        r"\bcucumber\b", r"\bkheera\b", r"\bvegetable(?!\s+(rack|cutter|chopper|slicer))\b", r"\bvegetables\b", r"\bfruit\b",
        r"\bfruits\b", r"\bdry\s*fruit\b", r"\bdry\s*fruits\b", r"\balmond\b", r"\bbadam\b",
        r"\bcashew\b", r"\bkaju\b", r"\bpistachio\b", r"\bpista\b", r"\bwalnut\b",
        r"\bakhorot\b", r"\bpeanut\b", r"\bmoongphali\b", r"\bdates\b", r"\bkhajoor\b",
        r"\braisin\b", r"\bkishmish\b",
    ],
    "Baby Care": [
        r"\bbaby\s*milk\b", r"\binfant\s*formula\b", r"\blactogen\b", r"\bcerelac\b",
        r"\bbaby\s*food\b", r"\bbaby\s*cereal\b", r"\bfeeder\b", r"\bbaby\s*bottle\b",
        r"\bteether\b", r"\bbaby\s*lotion\b", r"\bbaby\s*oil\b", r"\bbaby\s*soap\b",
        r"\bbaby\s*powder\b", r"\bjohnson\b", r"\bcanbebe\b", r"\bmolfix\b",
    ],
    "Electronics & Mobile": [
        r"\bcharger\b", r"\bcable\b", r"\busb\b", r"\bdata\s*cable\b", r"\bearphone\b",
        r"\bearphones\b", r"\bheadphone\b", r"\bheadphones\b", r"\bpower\s*bank\b",
        r"\badapter\b", r"\bled\b", r"\bbulb\b", r"\btorch\b", r"\bcalculator\b",
        r"\bextension\b", r"\bplug\b", r"\bsocket\b", r"\bmouse\b", r"\bkeyboard\b",
    ],
    "Stationery & Books": [
        r"\bpen(?!\s+(candel|drive))\b", r"\bpens\b", r"\bpencil(?!\s+(lip|eye))\b", r"\bpencils\b", r"\beraser\b", r"\bsharpener\b",
        r"\bscale\b", r"\bruler\b", r"\bnotebook\b", r"\bcopy\b", r"\bregister\b",
        r"\bmarker\b", r"\bmarkers\b", r"\bhighlighter\b", r"\bcolor(?!\s+(hair|smog))\b", r"\bcolors\b",
        r"\bpaint\b", r"\bscissors\b", r"\btape\b", r"\bglue\b", r"\bstick\b", r"\bstapler\b",
        r"\bpins\b", r"\bpaper\b", r"\ba4\b", r"\bfile\b", r"\bfolder\b",
    ],
}

# Compile regular expressions for ultra-high speed matching
COMPILED_RULES: list[tuple[str, re.Pattern]] = [
    (category_name, re.compile("|".join(patterns), re.IGNORECASE))
    for category_name, patterns in CATEGORY_RULES.items()
]


def classify_product_name(
    product_name: str,
    categories_by_name: dict[str, Category],
) -> tuple[int | None, str | None]:
    """
    Classifies a product name against retail archetype rules.
    Returns: (category_id, category_name)
    - If mapped to an existing active DB Category: (category.id, None)
    - If mapped to an archetype not yet in DB: (None, archetype_name)
    - If no rule matches: (None, None)
    """
    if not product_name:
        return None, None

    cleaned_name = clean_product_name(product_name)
    if not cleaned_name:
        return None, None

    for archetype_name, pattern in COMPILED_RULES:
        if pattern.search(cleaned_name):
            # Check if an existing Category in DB matches this archetype (case-insensitive)
            matched_category = categories_by_name.get(archetype_name.casefold())
            if matched_category:
                return matched_category.id, None
            
            # Check for partial / fuzzy existing category matches
            for cat_name_lower, cat_obj in categories_by_name.items():
                if (
                    archetype_name.lower() in cat_name_lower
                    or cat_name_lower in archetype_name.lower()
                ):
                    return cat_obj.id, None

            # Archetype is a new category candidate
            return None, archetype_name

    return None, None
