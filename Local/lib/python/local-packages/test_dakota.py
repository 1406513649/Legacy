from dakota import DakotaModel

# Create the model and set global options (populates the "environment" block)
dm = DakotaModel('my-model', tabular_data=True, error_file=True,
                 output_file=True, graphics=True)

# Create a group of variables
vars_1 = dm.Variables('vars-1')
v1 = vars_1.NormalUncertain('E', 5, 1)
v2 = vars_1.NormalUncertain('Nu', .3, .1, lower_bound=0.)
vars_1.uncertain_correlation_matrix(v1.descriptor, v2.descriptor, .8)

# Create a response
resp_1 = dm.Responses('resp-1')
resp_1.response('S')
resp_1.response('E')

# Define the interface
i = dm.Interfaces('inter-1', asynchronous=2)
d = i.analysis_drivers('driver.py')
d.work_directory(named='work/work', tag=True, link_files=('it', 'that'))

# Define the model, populating its variables and responses
model = dm.Model('model-1', vars_1, resp_1)
method = dm.Method('sampling', model_pointer=model, samples=10,
        max_iterations=40, backfill=True, convergence_tolerance=1e-8,
        fixed_seed=True, sample_type='lhs')

# Set this method as the top method
dm.top_method_pointer = method

# Write the input to file (the calls to run and check_input below do 
# this under the hood)
#dm.write_input()

# check input
dm.check_input()

# check_input will throw an error if fails
dm.run()
