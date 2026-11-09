from django.core.management.base import BaseCommand
from results.models import Student, ClassLevel

class Command(BaseCommand):
    help = 'Imports students and ensures they are assigned to the correct ClassLevel'

    def handle(self, *args, **kwargs):
        data = """
Nursery: Adewale Morisuko, Abass Mustapha, Alalade Azeemah, Akiode Nimotalai, Bello Abduljamal, Dauda Samiat, Odubade Michael, Onah Prosper, Oladipupo Iremipe, Oyewo Irewami, Raimi Aishat, Oyewo Mulero Daniel, Sofela Obaloluwa, Sokunle Inayatullai, Sowole Christiana, Sobayo Tiresimi, Shogbola Abdulbasit, Tairu Rachael
Kindergarten 1: Adeyemi Samuel, Ajibade Akorede, Atanda Adedumola, Babatunde Roqeebah, Balogun Ali, Fatoki Hameedah, Mureni Deborah Mutminah, Ogunwolu Moridiah, Ogundipe Tofunmi, Olayemi Oladayo, Owokade Adebimpe, Popoola Alicia, Sodiya Muhammad, Sowemimo Jalaldeen, Sodunke Iman, Raimi Misturah, Taiwo Abdulmumin, Saheed Kehinde, Saheed Taiwo
Kindergarten 2: Aboderin Marvelous, Adebayo Habeeb, Adegbiji Ibraheem, Babajide Quayum, Bello Malik, Awoleye Desmond, Dahunsi Gabriel, Kolawole Hakeemot, Gayiu Mohammed, Musibau Rodiat, Ogungbola Ezekiel, Olugbemi Odunayo, Oyebode Imade, Orunsolu Abdulahi, Orunsolu Yusrah, Yusuf Hamod, Adedamola Anuoluwa
Primary 1: Adebowale Emmanuel, Akisanmi Samuel, Abati Dorcas, Adegbiyi Ibrahim, Awelewa Emmanuella, Ayo-Vaughun Ayomide, Alani Ramadan, Atobatele Fatimah, Babatunde Al-ameen, Fasanya Dorah, Jacob Divine, Kolawole Abdulhakeem, Olalekan Darasimi, Odeyale Olamide, Odewunmi Ojumirayo, Oladele Alim, Owolabi Hassan, Owokade Adeyemi, Philip Mimisola, Solola Ireoluwa, Wahaab Ebunoluwa, Yusuf Nimotalai
Primary 2: Akanbi Olamide, Abiola Mahmudah, Assiha Faith, Awoleye Richard, Babajide Quazeem, Femi-Alagbe Michael, James Precious, Odubade Stephen, Ogundele Victoria, Ojo Elizabeth, Ogunbiyi Ifeoluwa, Odeyale Ayomide, Oke Rachael, Saheed Kamal, Salisu Mamud, Sodiya Moridiah
Primary 3: Adebayo Aishat, Adewale Nimotallai, Aje David Olamiposi, Ajayi Mafusoh, Akinwande Moridyu, Ajayi Oreoluwa, Alani Fuad, Ayede Hamod, Dada Goodnews, Durojaye Pamilerin, Fasanya Dominion, Idowu Damilare, Josephs Jordan, Kenneth Emmanuella, Lasisi Faruq, Ogungbola Michael, Oguntoyinbo Shinaayomi, Oladele Aliat, Olubayo Deborah, Olaogun Daniel, Owolabi Rachael, Sodunke Alimoh
Primary 4: Abass Abdulmajeed, Abass Ramadan, Abimbola Ameedah, Adeogun Toheebah, Adetula Daniel, Akiyemi Blessing, Babatunde Hamzat, Dauda Okikiola, Dosumu Roqueeb, Abdulfatai Mamudah, Jacob Oluwakemi, Odunewu Quayum, Ojo Sofiat, Olasupo Balikis, Oyewo Ireoluwa, Saheed Fuhad, Seteolu Sofiat, Sosanya Quam
Primary 5: Abiola Jabar, Adetula Victor, Adetula Samson, Ajibade Ajoke, Josephs Kadeisha, Lots Nancy, Ojo Iyabo, Ogunbiyi Israel, Babatunde Roqueeb, Owokade Adebisi, Oladipupo Firepemi, Odewunmi Shindara, Shokunle Isreal, Tairu Emmanuel, Taiwo Misturah
Primary 6: Adegbaye John, Adewale Moridiah, Afolabi Mosuru, Adeyemi Praise, Afolabi Semiat, Ajayi Inioluwa, Akinwande Moridiyat, Alasela Zeenat, Bakenne Mubaraka, Fasanya Daniel, James Divine, Ogundipe Teslimot, Babajide Quawiy, Olubayo Gideon, Olasupo Aliah, Owolabi Sultan, Onah Gold, Orunsolu Maheed, Adebowale Jomiloju
JSS 1: Afuwape Oluwajomiloju, Aje Daniel, Ayinde Baleen, Asorona Demilade, Idowu Success, Jamiu Obaloluwa, Fasina Abdullahi, Kolade Iyanuoluwa, Ogunremi Ajoke, Oladele Mariam, Oladugba Emmanuel, Olagoke Araire, Osho Abdulwahab
JSS 2: Abimbola Haliyah, Akindele Precious, Akindele Irewamiri, Akungbade Sofiat, Adeboye Dorcas, Alasela Abdulrahmon, Asogba Shulamite, Durodola Samod, Durowoju Moridia, Josephs Jason, Odubiyi Ayomide, Oladehinde Ayomikun, Omodara Mercy, Osahon Stellamaris, Oloyede Favour, Owolabi Mariam, Musa Abdulrahmon, Somoye Moridiyah, Sode Ilyas, Raji Halmod, Adetula Imole, Lasisi Lateefat
JSS 3: Abidemi Oluwasenilore, Abdul-Gafar Ibrahim, Adelekan Victoria, Agboola Islamiat, Agunbiade Quadri, Busari Boluwatife, Balogun Farihan, Gbeminiyi Emmanuel, Kuye Florence, Muideen Idris, Obajeminini Fulhad, Ogundele Esther, Oguntoyinbo Mosunmola, Olanrewaju Ayomide, Olasupo Samod, Olayinka Malik, Senibana Sofiat, Shodunke Faridah, Rufei Boluwatife, Tairu Daniel, Taiwo Mustekeem, Adetula Israel
SSS 1: Abimbola Muiz, Adewale Mujidat, Adetula Abigeal, Akanbi Muhammed, Bakenne Fatima, Durowoju Hamzat, Dosunmu Sofiat, Ogunbona Sofiat, Oladeji Rashid
SSS 2: Abdulwaheed Abdulsalam, Oladipupo Aliah, Olalekan Aliat, Olamilekan Khaleed, Olorunda Fisayomi, Raji Quazeem
        """

        lines = data.strip().split('\n')
        for line in lines:
            if ':' not in line: continue
            
            class_name, students_text = line.split(':')
            level, _ = ClassLevel.objects.get_or_create(name=class_name.strip())
            
            student_names = students_text.split(',')
            for full_name in student_names:
                full_name = full_name.strip()
                if not full_name: continue
                
                parts = full_name.split(' ')
                f_name = parts[0]
                l_name = " ".join(parts[1:]) if len(parts) > 1 else "Student"
                
                # This finds the student and updates their class
                # It matches based on first and last name
                Student.objects.filter(
                    first_name=f_name, 
                    last_name=l_name
                ).update(current_class=level)

        self.stdout.write(self.style.SUCCESS('SUCCESS: All students assigned to their classes!'))