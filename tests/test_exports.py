__author__ = 'michal'

from unittest import TestCase, mock
from toddler import Document

class TestExports(TestCase):

    def setUp(self):

        doc = Document()

        doc.url = "http://www.erafrance.com/annonce-immobiliere/" \
                  "JCZ01-541/Appartement-3-Pieces-A-vendre-MANDEL" \
                  "IEU-LA-NAPOULE&acm=JCZ01"

        doc.features = {
            "pipeline_name": "noap",
            "title": "Appartement 3 Pièces A vendre MANDELIEU LA NAPOULE",
            "features": """Prix : 350 000 €   ERA - Conversion monétaire
             Simulateur financement
             Transaction : A vendre
             Type de bien : Appartement
             Nombre de pièces : 3
             Nombre de chambres : 2
             Surface habitable (environ) : 69 m""",
            "description": """Votre agence ERA vous propose à la vente,
             un beau 3 pièces de 70 m² à Mandelieu. Idéalement situé à
             Cannes Marina au 3ème étage, vous bénéficiez d''une vue
             imprenable sur la piscine. L''appartement se compose d''un
             hall d''entrée, d''un séjour donnant sur une terrasses avec
             vue sur la piscine, d''une cuisine indépendante et toute équipée,
             de deux chambres, d''une salle de bain, d''un wc, et de nombreux
             placards. Place de parking et cave. Pour plus d''information
             n''hésitez pas à contacter notre agence immobilière
             au 04.93.48.60.60.""",
            "xlocation": "MANDELIEU LA NAPOULE, Alpes Maritimes"
        }

        self.doc = doc


    def test_nimbusview(self):

        from toddler.exports import nimbusview

        response = nimbusview.push_document(
            document=self.doc,
            push_api_url="http://banshee.hosting.lan.ifresearch.org:10302"
        )

        self.assertEqual(response.status_code, 200)